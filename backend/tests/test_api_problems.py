import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.problems.truss.generator import truss_generator


@pytest.mark.asyncio
async def test_list_problem_types():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/problems/types")
        assert response.status_code == 200
        data = response.json()
        assert "problem_types" in data
        assert "truss" in data["problem_types"]


@pytest.mark.asyncio
async def test_generate_truss_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/problems/truss/generate", json={"seed": 42}
        )
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


@pytest.mark.asyncio
async def test_check_truss_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seed = 100
        solution = truss_generator.solve(seed)

        answers = {}
        for member_key, mem_data in solution["member_solutions"].items():
            answers[member_key] = mem_data["magnitude"]
            answers[f"{member_key}_state"] = mem_data["state"]

        response = await client.post(
            "/api/v1/problems/truss/check",
            json={"seed": seed, "answers": answers, "tolerance": 0.01},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_passed"] is True
        assert data["score"] == 1.0
