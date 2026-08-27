"""Package exposing all application Pydantic data schemas and contracts."""

from app.schemas.admin import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    CourseCreateRequest,
    CourseInstructorCreateRequest,
    CourseInstructorRoleUpdate,
    CourseUpdateRequest,
    ProblemSlotSpec,
    PublishAssignmentRequest,
    RosterEntryCreate,
    RosterImportRequest,
)
from app.schemas.auth import (
    InstructorLoginRequest,
    InstructorRegisterRequest,
    StudentLoginRequest,
    StudentRegisterRequest,
)
from app.schemas.student import StudentInvitationActionRequest

__all__ = [
    "AssignmentCreateRequest",
    "AssignmentUpdateRequest",
    "CourseCreateRequest",
    "CourseInstructorCreateRequest",
    "CourseInstructorRoleUpdate",
    "CourseUpdateRequest",
    "InstructorLoginRequest",
    "InstructorRegisterRequest",
    "ProblemSlotSpec",
    "PublishAssignmentRequest",
    "RosterEntryCreate",
    "RosterImportRequest",
    "StudentInvitationActionRequest",
    "StudentLoginRequest",
    "StudentRegisterRequest",
]
