import os
import sqlite3
from flask import g
from app.config import Config


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
        g.db = sqlite3.connect(Config.DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                predicted_category TEXT,
                predicted_urgency TEXT,
                category_confidence REAL,
                priority_confidence REAL,
                admin_response TEXT,
                handled_by TEXT,
                status TEXT,
                created_at TIMESTAMP
            )
            """
        )
        # Ensure complaint metadata columns exist (non-destructive for existing table)
        existing = db.execute("PRAGMA table_info(complaints)").fetchall()
        # Normalize column names from returned rows
        col_names = []
        for r in existing:
            try:
                # sqlite3.Row or tuple-like
                col_names.append(r[1])
            except Exception:
                try:
                    col_names.append(r["name"])
                except Exception:
                    pass

        if "category_confidence" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN category_confidence REAL")
        if "priority_confidence" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN priority_confidence REAL")
        if "admin_response" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN admin_response TEXT")
        if "handled_by" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN handled_by TEXT")
        if "category_source" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN category_source TEXT")
        if "priority_source" not in col_names:
            db.execute("ALTER TABLE complaints ADD COLUMN priority_source TEXT")

        # Ensure pending_categories table exists
        create_pending_categories_table(db)
        
        # Ensure promoted column exists on pending_categories (non-destructive)
        pending_info = db.execute("PRAGMA table_info(pending_categories)").fetchall()
        pending_cols = []
        for r in pending_info:
            try:
                pending_cols.append(r[1])
            except Exception:
                try:
                    pending_cols.append(r["name"])
                except Exception:
                    pass

        if "promoted" not in pending_cols:
            db.execute("ALTER TABLE pending_categories ADD COLUMN promoted INTEGER DEFAULT 0")
        db.commit()
    app.teardown_appcontext(close_db)


def create_pending_categories_table(db=None):
    """Create the pending_categories table if it does not exist.

    Columns:
    - id INTEGER PRIMARY KEY AUTOINCREMENT
    - category_name TEXT UNIQUE NOT NULL
    - complaint_count INTEGER DEFAULT 1
    - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - promoted INTEGER DEFAULT 0  -- 0 = pending, 1 = promoted
    """
    close_after = False
    if db is None:
        db = get_db()
        close_after = False

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL,
            complaint_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            promoted INTEGER DEFAULT 0
        )
        """
    )


def get_pending_categories():
    """Return all pending categories ordered by complaint_count desc then created_at desc."""
    db = get_db()
    rows = db.execute(
        "SELECT id, category_name, complaint_count, created_at FROM pending_categories ORDER BY complaint_count DESC, datetime(created_at) DESC"
    ).fetchall()
    return rows


def add_or_increment_pending_category(category_name):
    """Add a new pending category or increment complaint_count if it exists.

    Leading/trailing whitespace in `category_name` is stripped before comparison.
    """
    if not category_name:
        return None

    name = category_name.strip()
    if not name:
        return None

    db = get_db()
    # Check if exists (safe comparison after stripping)
    existing = db.execute(
        "SELECT id, complaint_count FROM pending_categories WHERE category_name = ?",
        (name,)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE pending_categories SET complaint_count = complaint_count + 1 WHERE id = ?",
            (existing[0],)
        )
    else:
        db.execute(
            "INSERT INTO pending_categories (category_name, complaint_count) VALUES (?, ?)",
            (name, 1)
        )

    db.commit()
    db.commit()
    return True


def get_promotable_categories(threshold=10):
    """Return pending categories eligible for promotion.

    A category is promotable when complaint_count >= threshold and promoted is 0 or NULL.
    """
    db = get_db()
    rows = db.execute(
        "SELECT id, category_name, complaint_count, created_at FROM pending_categories "
        "WHERE complaint_count >= ? AND (promoted IS NULL OR promoted = 0) "
        "ORDER BY complaint_count DESC, datetime(created_at) DESC",
        (threshold,)
    ).fetchall()
    return rows


def promote_category(category_name):
    """Mark a pending category as promoted (set promoted = 1).

    Returns True if a row was updated, False otherwise.
    """
    if not category_name:
        return False
    name = category_name.strip()
    if not name:
        return False

    db = get_db()
    cur = db.execute(
        "UPDATE pending_categories SET promoted = 1 WHERE category_name = ? AND (promoted IS NULL OR promoted = 0)",
        (name,)
    )
    db.commit()
    return cur.rowcount > 0


def get_promoted_categories():
    """Return categories that have been promoted (promoted = 1)."""
    db = get_db()
    rows = db.execute(
        "SELECT id, category_name, complaint_count, created_at FROM pending_categories WHERE promoted = 1 ORDER BY datetime(created_at) DESC"
    ).fetchall()
    return rows
