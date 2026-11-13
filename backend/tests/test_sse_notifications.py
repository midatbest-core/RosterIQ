import asyncio
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.notifications import create_notification
from app.modules.auth.broadcaster import broadcaster
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_sse_notifications_delivery_and_isolation(db_session: Session):
    def override_db():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_db
    try:
        db = db_session
        pwd = hash_password("Pass1234!")
        
        # Create two test users
        u1 = User(
            id=uuid.uuid4(),
            email=f"sse_u1_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=pwd,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        u2 = User(
            id=uuid.uuid4(),
            email=f"sse_u2_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=pwd,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        db.add_all([u1, u2])
        db.commit()

        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client1, \
                   AsyncClient(transport=transport, base_url="http://test") as client2:

            # 1. Test unauthenticated SSE -> 401 Unauthorized
            unauth_resp = await client1.get("/api/v1/auth/notifications/stream")
            assert unauth_resp.status_code == 401

            # 2. Login User 1 and User 2
            resp1 = await client1.post("/api/v1/auth/login", json={"email": u1.email, "password": "Pass1234!"})
            assert resp1.status_code == 200

            resp2 = await client2.post("/api/v1/auth/login", json={"email": u2.email, "password": "Pass1234!"})
            assert resp2.status_code == 200

            # 3. Direct Broadcaster subscribe & isolation test
            q1_a = await broadcaster.subscribe(u1.id)
            q1_b = await broadcaster.subscribe(u1.id)  # multiple concurrent connections for user 1
            q2 = await broadcaster.subscribe(u2.id)

            # Publish a notification directed ONLY to user 1
            test_payload = {
                "id": str(uuid.uuid4()),
                "title": "Shift Assigned",
                "message": "You have a new shift",
                "is_read": False,
            }
            await broadcaster.publish(u1.id, test_payload)

            # User 1 queues should receive it
            rec_a = await asyncio.wait_for(q1_a.get(), timeout=1.0)
            rec_b = await asyncio.wait_for(q1_b.get(), timeout=1.0)
            assert rec_a["title"] == "Shift Assigned"
            assert rec_b["title"] == "Shift Assigned"

            # User 2 queue should NOT receive it (Isolation check)
            assert q2.empty()

            # Publish to User 2
            test_payload2 = {
                "id": str(uuid.uuid4()),
                "title": "Leave Approved",
                "message": "Your leave is approved",
                "is_read": False,
            }
            await broadcaster.publish(u2.id, test_payload2)
            rec2 = await asyncio.wait_for(q2.get(), timeout=1.0)
            assert rec2["title"] == "Leave Approved"

            # User 1 queues should NOT have received User 2's notification
            assert q1_a.empty()
            assert q1_b.empty()

            # Clean up
            await broadcaster.unsubscribe(u1.id, q1_a)
            await broadcaster.unsubscribe(u1.id, q1_b)
            await broadcaster.unsubscribe(u2.id, q2)

            # 4. Test Disconnect -> Notification created in DB -> Reconnect fetch recovery
            # User 1 disconnects (no active queue in broadcaster)
            # A notification is created for User 1 while offline
            notif_offline = create_notification(
                db=db,
                user_id=u1.id,
                title="Urgent Schedule Change",
                message="Your schedule for tomorrow has been updated.",
                notification_type="ROSTER_CHANGE",
            )
            db.commit()

            # User 1 reconnects / fetches persistent notifications
            list_resp = await client1.get("/api/v1/auth/notifications")
            assert list_resp.status_code == 200
            notifications_list = list_resp.json()
            assert any(n["id"] == str(notif_offline.id) for n in notifications_list)
            assert any(n["title"] == "Urgent Schedule Change" for n in notifications_list)

            # Mark notification as read
            read_resp = await client1.post(f"/api/v1/auth/notifications/{notif_offline.id}/read")
            assert read_resp.status_code == 200

            # Verify state in database
            db.refresh(notif_offline)
            assert notif_offline.is_read is True
    finally:
        app.dependency_overrides.clear()



