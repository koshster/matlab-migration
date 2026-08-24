"""Package exposing all SQLAlchemy ORM models for the Statics Platform.

Re-exports user, course, roster, and assignment entities so that all external
modules (Alembic, services, routers, seed scripts) can import cleanly from
`app.db.models`.
"""

from app.db.models.assignments import (
    Assignment,
    AssignmentProblem,
    AssignmentTarget,
    StudentAssignment,
    Submission,
)
from app.db.models.courses import (
    Course,
    CourseEnrollment,
    CourseInstructor,
    RosterEntry,
)
from app.db.models.users import (
    Instructor,
    Student,
)

__all__ = [
    "Assignment",
    "AssignmentProblem",
    "AssignmentTarget",
    "Course",
    "CourseEnrollment",
    "CourseInstructor",
    "Instructor",
    "RosterEntry",
    "Student",
    "StudentAssignment",
    "Submission",
]
