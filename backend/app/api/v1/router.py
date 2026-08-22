from fastapi import APIRouter

from app.api.v1 import assignments, auth, health, problems

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(auth.router)
router.include_router(assignments.router)
router.include_router(problems.router)
