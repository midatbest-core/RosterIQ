from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.auth.notification_models import Notification


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> Notification:
    """Creates and persists an in-app notification record."""
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_type=reference_type,
        reference_id=reference_id,
        is_read=False,
    )
    db.add(notif)
    return notif


def notify_managers(
    db: Session,
    title: str,
    message: str,
    notification_type: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> list[Notification]:
    """Broadcasts a persistent notification to all active Operations Managers and Admins."""
    managers = db.scalars(
        select(User).where(
            User.role.in_([UserRole.ADMIN, UserRole.OPERATIONS_MANAGER]),
            User.is_active == True,
        )
    ).all()
    created = []
    for mgr in managers:
        n = create_notification(
            db=db,
            user_id=mgr.id,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        created.append(n)
    return created

