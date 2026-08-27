"""Pydantic data schemas for authentication and user account management.

Defines input validation and serialization models for student and instructor
registration and login endpoints.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.identity import looks_like_email, normalize_email

_MIN_PASSWORD_LENGTH = 8


class _EmailBody(BaseModel):
    """Base schema validating and normalizing email inputs."""

    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        if not looks_like_email(value):
            raise ValueError("not a valid email address")
        return normalize_email(value)


class StudentRegisterRequest(BaseModel):
    """Student registration input payload."""

    pid: str = Field(
        min_length=1,
        max_length=32,
        description="University Student ID (e.g. A10000001)",
    )
    firstName: str = Field(
        min_length=1,
        max_length=128,
        description="First given name",
    )
    lastName: str = Field(
        min_length=1,
        max_length=128,
        description="Last family name",
    )
    password: str = Field(
        min_length=_MIN_PASSWORD_LENGTH,
        description="Account password (min 8 chars)",
    )


class StudentLoginRequest(BaseModel):
    """Student login input payload."""

    pid: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1)


class InstructorRegisterRequest(_EmailBody):
    """Instructor/TA account registration payload."""

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Full name with title",
    )
    password: str = Field(
        min_length=_MIN_PASSWORD_LENGTH,
        description="Account password (min 8 chars)",
    )


class InstructorLoginRequest(_EmailBody):
    """Instructor/TA login input payload."""

    password: str = Field(min_length=1)
