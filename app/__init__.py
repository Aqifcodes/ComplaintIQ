import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from app.config import Config
from app.database import get_db, init_db
from app.predictor import predict_complaint


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.secret_key = app.config.get("SECRET_KEY")

    init_db(app)

    @app.template_filter("format_datetime")
    def format_datetime(value):
        """Format a datetime for UI display as '08 Aug 2026 · 1:59 PM'."""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return f"{value.strftime('%d %b %Y')} · {value.strftime('%I:%M %p').lstrip('0')}"

    @app.route("/")
    def home():
        user_id = session.get("user_id")
        if user_id:
            db = get_db()
            user = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
            if user:
                if user["role"] == "Admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("customer_dashboard"))
            session.clear()
        return render_template("auth/login.html")

    @app.route("/login")
    def login():
        if session.get("user_id"):
            return redirect(url_for("home"))
        return render_template("auth/login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/signup")
    def signup():
        if session.get("user_id"):
            return redirect(url_for("home"))
        return render_template("auth/signup.html")

    @app.route("/api/auth/signup", methods=["POST"])
    def api_signup():
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        confirm_password = data.get("confirmPassword") or ""

        if not name or not email or not password or not confirm_password:
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        db = get_db()
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            return jsonify({"success": False, "message": "Email address already exists."}), 400

        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, "Customer")
        )
        db.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully! Please sign in.",
            "user": {"name": name, "email": email}
        })

    @app.route("/api/auth/login", methods=["POST"])
    def api_login():
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required."}), 400

        db = get_db()
        user = db.execute(
            "SELECT id, full_name, email, password, role FROM users WHERE email = ?", (email,)
        ).fetchone()

        if not user:
            return jsonify({"success": False, "message": "No account found with that email address."}), 401

        if not check_password_hash(user["password"], password):
            return jsonify({"success": False, "message": "Incorrect email or password."}), 401

        session["user_id"] = user["id"]
        session["user_role"] = user["role"]
        session["user_name"] = user["full_name"]

        return jsonify({
            "success": True,
            "message": "Welcome back to ComplaintIQ!",
            "user": {
                "name": user["full_name"],
                "email": user["email"],
                "role": user["role"]
            }
        })

    @app.route("/customer/dashboard", methods=["GET", "POST"])
    def customer_dashboard():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))

        db = get_db()
        user = db.execute("SELECT id, full_name, role, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for("login"))

        if user["role"] != "Customer":
            return redirect(url_for("admin_dashboard"))

        message = None
        title_value = ""
        description_value = ""

        if request.method == "POST":
            title_value = (request.form.get("title") or "").strip()
            description_value = (request.form.get("description") or "").strip()

            if not title_value or not description_value:
                message = "Title and description are required."
            else:
                # Combine title and description for prediction
                combined_text = f"{title_value} {description_value}"
                predicted_category = None
                predicted_priority = None
                category_confidence = None
                priority_confidence = None
                preds = None
                try:
                    preds = predict_complaint(combined_text)
                    predicted_category = preds.get("category")
                    predicted_priority = preds.get("priority")
                    # Convert to float or None
                    category_confidence = float(preds.get("category_confidence") or 0.0)
                    priority_confidence = float(preds.get("priority_confidence") or 0.0)
                except Exception:
                    # If prediction fails, continue saving the complaint without ML outputs
                    predicted_category = None
                    predicted_priority = None
                    category_confidence = None
                    priority_confidence = None

                handled_by = preds.get("handled_by") if preds else None
                category_source = preds.get("category_source") if preds else None
                priority_source = preds.get("priority_source") if preds else None
                db.execute(
                    "INSERT INTO complaints (user_id, title, description, predicted_category, predicted_urgency, category_confidence, priority_confidence, handled_by, category_source, priority_source, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        title_value,
                        description_value,
                        predicted_category,
                        predicted_priority,
                        category_confidence,
                        priority_confidence,
                        handled_by,
                        category_source,
                        priority_source,
                        "Awaiting Response",
                        datetime.utcnow().isoformat(sep=" ")
                    )
                )
                db.commit()
                message = "Complaint submitted successfully."
                title_value = ""
                description_value = ""

        complaints = db.execute(
            "SELECT id, title, description, status, created_at, admin_response FROM complaints WHERE user_id = ? ORDER BY datetime(created_at) DESC",
            (user_id,)
        ).fetchall()

        return render_template(
            "customer/dashboard.html",
            user_name=user["full_name"],
            user_email=user["email"],
            user_role=user["role"],
            message=message,
            title=title_value,
            description=description_value,
            complaints=complaints
        )

    @app.route("/admin/dashboard")
    def admin_dashboard():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))

        db = get_db()
        user = db.execute("SELECT id, full_name, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for("login"))

        if user["role"] != "Admin":
            return redirect(url_for("customer_dashboard"))

        from app.gemini_service import get_current_official_categories
        
        # Get official categories (including promoted ones)
        categories = get_current_official_categories()
        
        # Also fetch any pending categories that are in the pending_categories table
        pending_rows = db.execute("SELECT category_name FROM pending_categories").fetchall()
        for row in pending_rows:
            cat_name = row["category_name"]
            if cat_name not in categories:
                categories.append(cat_name)

        # Also fetch any distinct categories actually used in complaints (as a fallback)
        actual_rows = db.execute("SELECT DISTINCT predicted_category FROM complaints WHERE predicted_category IS NOT NULL").fetchall()
        for row in actual_rows:
            cat_name = row["predicted_category"]
            if cat_name not in categories:
                categories.append(cat_name)
                
        categories.sort()

        complaints = db.execute(
            "SELECT id, title, predicted_category, predicted_urgency, category_confidence, priority_confidence, category_source, priority_source, status, admin_response, created_at FROM complaints ORDER BY datetime(created_at) DESC"
        ).fetchall()

        return render_template(
            "admin/dashboard.html",
            user_name=user["full_name"],
            user_role=user["role"],
            complaints=complaints,
            categories=categories
        )

    @app.route("/admin/complaint/<int:complaint_id>", methods=["GET", "POST"])
    def admin_complaint_detail(complaint_id):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))

        db = get_db()
        user = db.execute("SELECT id, full_name, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for("login"))

        if user["role"] != "Admin":
            return redirect(url_for("customer_dashboard"))

        complaint = db.execute(
            "SELECT id, title, description, predicted_category, category_confidence, predicted_urgency, priority_confidence, handled_by, category_source, priority_source, status, created_at, admin_response FROM complaints WHERE id = ?",
            (complaint_id,)
        ).fetchone()

        if not complaint:
            return redirect(url_for("admin_dashboard"))

        message = None

        if request.method == "POST":
            requested_response = (request.form.get("admin_response") or "").strip()
            if requested_response:
                db.execute(
                    "UPDATE complaints SET admin_response = ?, status = ? WHERE id = ?",
                    (requested_response, "Resolved", complaint_id)
                )
                db.commit()
                message = "Complaint status updated successfully."
                complaint = db.execute(
                    "SELECT id, title, description, predicted_category, category_confidence, predicted_urgency, priority_confidence, handled_by, category_source, priority_source, status, created_at, admin_response FROM complaints WHERE id = ?",
                    (complaint_id,)
                ).fetchone()
            else:
                message = "Please enter a response before submitting."

        return render_template(
            "admin/complaint_detail.html",
            user_name=user["full_name"],
            user_role=user["role"],
            complaint=complaint,
            message=message
        )

    return app