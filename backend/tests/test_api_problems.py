import uuid
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_student_id
from app.main import app


def _as_signed_in_student() -> None:
    """These debug routes require a session; the cookie itself isn't under test."""
    app.dependency_overrides[get_current_student_id] = lambda: uuid.uuid4()


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_problem_routes_require_a_session() -> None:
    """Unauthenticated access would expose the generator to the open internet."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/problems/types")).status_code == 401
        assert (
            await client.post("/api/v1/problems/truss/generate", json={"seed": 42})
        ).status_code == 401


@pytest.mark.asyncio
async def test_answer_oracle_route_is_gone() -> None:
    """`POST /problems/{type}/check` graded a caller-supplied (seed, answers)
    pair without recording an attempt, letting answers be brute-forced one
    member at a time. It must stay deleted."""
    _as_signed_in_student()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/problems/truss/check",
            json={"seed": 100, "answers": {}, "tolerance": 0.01},
        )
        assert response.status_code in (404, 405)


@pytest.mark.asyncio
async def test_list_problem_types() -> None:
    _as_signed_in_student()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/problems/types")
        assert response.status_code == 200
        data = response.json()
        assert "problem_types" in data
        assert "truss" in data["problem_types"]


@pytest.mark.asyncio
async def test_generate_truss_api() -> None:
    _as_signed_in_student()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/problems/truss/generate", json={"seed": 42})
        assert response.status_code == 200
        data = response.json()
        assert data["problem_type"] == "truss"
        assert data["seed"] == 42
        assert len(data["visual_schema"]) > 0
        assert len(data["answer_schema"]) > 0

        # Verify security rule: no solution keys
        serialized = str(data)
        assert "member_solutions" not in serialized
        assert "reactions" not in serialized
