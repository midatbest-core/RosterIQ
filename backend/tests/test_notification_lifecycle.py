import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.notifications import create_notification
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_notification_deletion_and_isolation(db_session: Session):
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

        u1 = User(
            id=uuid.uuid4(),
            email=f"notif_u1_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=pwd,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        u2 = User(
            id=uuid.uuid4(),
            email=f"notif_u2_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=pwd,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        db.add_all([u1, u2])
        db.commit()

        n1 = create_notification(db, u1.id, "Shift Notice", "Your shift was assigned", "SHIFT_ASSIGN")
        n2 = create_notification(db, u2.id, "Leave Notice", "Your leave was reviewed", "LEAVE_STATUS")
        db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c1, \
                   AsyncClient(transport=transport, base_url="http://test") as c2:

            await c1.post("/api/v1/auth/login", json={"email": u1.email, "password": "Pass1234!"})
            await c2.post("/api/v1/auth/login", json={"email": u2.email, "password": "Pass1234!"})

            # 1. User 1 marks n1 as read
            r_read = await c1.post(f"/api/v1/auth/notifications/{n1.id}/read")
            assert r_read.status_code == 200

            # 2. User 2 cannot mark User 1's notification as read
            r_bad_read = await c2.post(f"/api/v1/auth/notifications/{n1.id}/read")
            assert r_bad_read.status_code == 404

            # 3. User 2 cannot delete User 1's notification
            r_bad_del = await c2.delete(f"/api/v1/auth/notifications/{n1.id}")
            assert r_bad_del.status_code == 404

            # 4. User 1 successfully deletes n1
            r_del = await c1.delete(f"/api/v1/auth/notifications/{n1.id}")
            assert r_del.status_code == 200
            assert r_del.json()["status"] == "deleted"

            # 5. Verify n1 is no longer in User 1's notifications
            r_list = await c1.get("/api/v1/auth/notifications")
            assert r_list.status_code == 200
            assert not any(item["id"] == str(n1.id) for item in r_list.json())
    finally:
        app.dependency_overrides.clear()


