from __future__ import annotations

import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.auth.notification_models import Notification
from app.modules.auth.broadcaster import broadcaster
from app.core.email import dispatch_email_background


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    send_email: bool = True,
) -> Notification:
    """Creates and persists an in-app notification record and broadcasts via SSE and optional email."""
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
    
    # Broadcast to active SSE listeners if event loop is running
    payload = {
        "id": str(notif.id),
        "user_id": str(notif.user_id),
        "title": notif.title,
        "message": notif.message,
        "notification_type": notif.notification_type,
        "reference_type": notif.reference_type,
        "reference_id": str(notif.reference_id) if notif.reference_id else None,
        "is_read": notif.is_read,
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcaster.publish(user_id, payload))
    except RuntimeError:
        pass

    # Non-blocking outbound email notification if enabled and recipient has email
    if send_email:
        user = db.get(User, user_id)
        if user and user.email and "@" in user.email:
            subject = f"[RosterIQ] {title}"
            body = f"Hello,\n\n{message}\n\nType: {notification_type}\n\nPlease log in to RosterIQ to review.\n\nBest regards,\nRosterIQ Team"
            dispatch_email_background([user.email], subject, body)

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

