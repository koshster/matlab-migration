"""Package composing all admin course, roster, and assignment controllers."""

from fastapi import APIRouter

from app.api.v1.admin.assignments import router as assignments_router
from app.api.v1.admin.courses import router as courses_router
from app.api.v1.admin.grades import router as grades_router
from app.api.v1.admin.roster import router as roster_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(courses_router)
router.include_router(roster_router)
router.include_router(assignments_router)
router.include_router(grades_router)

__all__ = ["router"]
