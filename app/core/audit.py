from sqlalchemy.orm import Session

from app.models.models import AuditLog, User


def log_action(
    db: Session,
    user: User | None,
    action: str,
    resource: str,
    resource_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()
    return entry
