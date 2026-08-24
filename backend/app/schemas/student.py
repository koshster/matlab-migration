"""Pydantic data schemas for student portal endpoints.

Defines serialization models for invitations, enrolled courses, and assignments.
"""

from pydantic import BaseModel


class StudentInvitationActionRequest(BaseModel):
    """Payload for accepting or declining a course invitation."""

    action: str  # "accept" or "decline"
