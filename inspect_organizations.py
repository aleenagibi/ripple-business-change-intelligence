from app.db.database import SessionLocal
from app.models.organization import Organization
from sqlalchemy import select

db = SessionLocal()

try:
    organizations = list(
        db.scalars(
            select(Organization)
            .order_by(Organization.created_at)
        ).all()
    )

    for organization in organizations:
        print(
            f"{organization.id} | "
            f"{organization.name}"
        )
finally:
    db.close()
