"""Instructors must be able to set (and clear) the dates that drive closure.

Before this, `due_at`, `opens_at` and `hard_deadline_at` were columns only the
seed script could write -- the admin request schemas had no date fields at all,
so deadline-based locking was unusable through the API.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id
from app.db.models import Course, Instructor
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Instructor(
                id=INSTRUCTOR_ID, email="dates@ucsd.edu", password_hash="h", name="Prof. Dates"
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
async def admin_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_instructor_id] = lambda: INSTRUCTOR_ID
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _course(db: AsyncSession) -> Course:
    course = Course(instructor_id=INSTRUCTOR_ID, code="MAE 200", term="Fall 2026")
    db.add(course)
    await db.flush()
    return course


@pytest.mark.asyncio
async def test_dates_round_trip_through_create(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    course = await _course(db_session)
    resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={
            "title": "Truss HW",
            "opensAt": "2026-10-01T00:00:00Z",
            "dueAt": "2026-12-15T23:59:00Z",
            "hardDeadlineAt": "2026-12-20T23:59:00Z",
            "allowLate": True,
            "revealSolutionsAfterClose": True,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["dueAt"].startswith("2026-12-15T23:59:00")
    assert body["revealSolutionsAfterClose"] is True
    # allow_late is on, so the hard deadline is the real cutoff.
    assert body["effectiveCloseAt"].startswith("2026-12-20T23:59:00")


@pytest.mark.asyncio
async def test_effective_close_follows_the_late_policy(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    course = await _course(db_session)
    resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={
            "title": "No late work",
            "dueAt": "2026-12-15T23:59:00Z",
            "hardDeadlineAt": "2026-12-20T23:59:00Z",
            "allowLate": False,
        },
    )
    # Late work forbidden -> the due date closes it, not the hard deadline.
    assert resp.json()["effectiveCloseAt"].startswith("2026-12-15T23:59:00")


@pytest.mark.asyncio
async def test_patch_can_clear_a_deadline(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    """An explicit null clears; an omitted field leaves the value alone."""
    course = await _course(db_session)
    created = (
        await admin_client.post(
            f"/api/v1/admin/courses/{course.id}/assignments",
            json={"title": "Clearable", "dueAt": "2026-12-15T23:59:00Z"},
        )
    ).json()
    aid = created["id"]

    # Omitting dueAt must not disturb it.
    untouched = await admin_client.patch(
        f"/api/v1/admin/assignments/{aid}", json={"title": "Renamed"}
    )
    assert untouched.json()["dueAt"] is not None

    cleared = await admin_client.patch(f"/api/v1/admin/assignments/{aid}", json={"dueAt": None})
    assert cleared.status_code == 200
    assert cleared.json()["dueAt"] is None
    assert cleared.json()["effectiveCloseAt"] is None


@pytest.mark.asyncio
async def test_naive_datetime_is_rejected(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A deadline without an offset is ambiguous; refuse rather than guess."""
    course = await _course(db_session)
    resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={"title": "Ambiguous", "dueAt": "2026-12-15T23:59:00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_out_of_order_dates_are_rejected_on_create(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    course = await _course(db_session)
    resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={
            "title": "Backwards",
            "opensAt": "2026-12-20T00:00:00Z",
            "dueAt": "2026-12-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_validates_against_the_stored_row(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A PATCH sending only dueAt must still agree with the stored deadline."""
    course = await _course(db_session)
    created = (
        await admin_client.post(
            f"/api/v1/admin/courses/{course.id}/assignments",
            json={"title": "Ordered", "hardDeadlineAt": "2026-12-10T00:00:00Z"},
        )
    ).json()

    resp = await admin_client.patch(
        f"/api/v1/admin/assignments/{created['id']}",
        json={"dueAt": "2026-12-25T00:00:00Z"},
    )
    assert resp.status_code == 400
    assert "hardDeadlineAt" in resp.json()["detail"]
