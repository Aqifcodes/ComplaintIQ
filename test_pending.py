print("TEST FILE STARTED")
from app import create_app
from app.gemini_service import gemini_classify_complaint
from app.database import get_db, add_or_increment_pending_category

app = create_app()

with app.app_context():

    result = gemini_classify_complaint(
        """
        I need assistance with managing the physical office building.
        This includes workplace facilities, building maintenance,
        office access areas, cleaning arrangements and facility operations.
        """,
        [
            "Technical Support",
            "Product Support",
            "Customer Service",
            "IT Support",
            "Billing and Payments",
            "Returns and Exchanges",
            "Service Outages and Maintenance",
            "Sales and Pre-Sales",
            "Human Resources",
            "General Inquiry"
        ]
    )

    print("\nGemini result:")
    print(result)

    if result["decision"] == "new":
        category = result["category"]
        add_or_increment_pending_category(category)
        print("\nAdded to pending:", category)
    else:
        print("\nExisting category -> nothing added")

    db = get_db()

    print("\nPending categories:")
    print(db.execute(
        "SELECT category_name, complaint_count FROM pending_categories"
    ).fetchall())