"""Course student roster import and management endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.helpers import _roster_entry_out
from app.core.identity import looks_like_email, normalize_email, normalize_pid
from app.db.models import Instructor, RosterEntry, Student
from app.db.session import get_db
from app.schemas.admin import RosterImportRequest
from app.services.authz import assert_course_role, require_instructor

router = APIRouter(tags=["admin-roster"])


class RosterStatusUpdateRequest(BaseModel):
    """Payload for updating a roster student's enrollment status."""

    status: str  # "invited", "active", "dropped"


@router.get("/courses/{course_id}/roster", summary="List course roster entries")
async def list_roster(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve full roster of enrolled and invited students for a course."""
    await assert_course_role(db, course_id, instructor, minimum="reader")
    entries = (
        (
            await db.execute(
                select(RosterEntry)
                .where(RosterEntry.course_id == course_id)
                .order_by(RosterEntry.invited_at.asc())
            )
        )
        .scalars()
        .all()
    )

    return [_roster_entry_out(e) for e in entries]


@router.post("/courses/{course_id}/roster", summary="Batch import roster entries")
async def add_roster_entries(
    course_id: uuid.UUID,
    body: RosterImportRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import roster rows, auto-linking existing student accounts and skipping duplicates."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    # Load existing roster entries to detect collisions
    existing_entries = (
        (await db.execute(select(RosterEntry).where(RosterEntry.course_id == course_id)))
        .scalars()
        .all()
    )

    existing_pids = {e.pid for e in existing_entries if e.pid}
    existing_emails = {e.email for e in existing_entries if e.email}

    # Preload all student accounts for lookup
    all_students = (await db.execute(select(Student))).scalars().all()
    students_by_pid = {s.pid.upper(): s for s in all_students}

    added_count = 0
    already_present_count = 0
    linked_count = 0
    invalid_count = 0
    row_results: list[dict[str, Any]] = []

    for row_idx, item in enumerate(body.entries, start=1):
        raw_pid = item.pid.strip() if item.pid else None
        raw_email = item.email.strip() if item.email else None
        first_name = item.firstName.strip() if item.firstName else None
        last_name = item.lastName.strip() if item.lastName else None

        pid = normalize_pid(raw_pid) if raw_pid else None
        email = normalize_email(raw_email) if raw_email else None

        # Validate entry
        if not pid and not email:
            invalid_count += 1
            row_results.append(
                {
                    "row": row_idx,
                    "outcome": "invalid",
                    "pid": pid,
                    "email": email,
                    "message": "At least one of PID or email must be provided",
                }
            )
            continue

        if email and not looks_like_email(email):
            invalid_count += 1
            row_results.append(
                {
                    "row": row_idx,
                    "outcome": "invalid",
                    "pid": pid,
                    "email": email,
                    "message": "Malformed email address",
                }
            )
            continue

        # Check duplicate
        if (pid and pid in existing_pids) or (email and email in existing_emails):
            already_present_count += 1
            row_results.append(
                {
                    "row": row_idx,
                    "outcome": "already_present",
                    "pid": pid,
                    "email": email,
                    "message": None,
                }
            )
            continue

        # Check if student account already exists
        matched_student = students_by_pid.get(pid) if pid else None
        if matched_student:
            student_id = matched_student.id
            outcome = "linked_existing_account"
            linked_count += 1
        else:
            student_id = None
            outcome = "added"
            added_count += 1

        new_entry = RosterEntry(
            course_id=course_id,
            student_id=student_id,
            pid=pid,
            email=email,
            first_name=first_name,
            last_name=last_name,
            status="invited",
        )
        db.add(new_entry)

        if pid:
            existing_pids.add(pid)
        if email:
            existing_emails.add(email)

        row_results.append(
            {
                "row": row_idx,
                "outcome": outcome,
                "pid": pid,
                "email": email,
                "message": None,
            }
        )

    await db.commit()

    return {
        "added": added_count,
        "linked": linked_count,
        "invalid": invalid_count,
        "alreadyPresent": already_present_count,
        "results": row_results,
        "summary": {
            "totalProcessed": len(body.entries),
            "added": added_count,
            "linkedExistingAccount": linked_count,
            "alreadyPresent": already_present_count,
            "invalid": invalid_count,
        },
        "rowResults": row_results,
    }


@router.patch("/courses/{course_id}/roster/{entry_id}", summary="Update roster entry status")
async def update_roster_entry_status(
    course_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: RosterStatusUpdateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a roster student's status (e.g. active, dropped)."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    entry = (
        await db.execute(
            select(RosterEntry).where(
                RosterEntry.id == entry_id,
                RosterEntry.course_id == course_id,
            )
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster entry not found")

    entry.status = body.status
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return _roster_entry_out(entry)


@router.delete(
    "/courses/{course_id}/roster/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete roster entry",
)
async def delete_roster_entry(
    course_id: uuid.UUID,
    entry_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a student from the course roster."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    entry = (
        await db.execute(
            select(RosterEntry).where(
                RosterEntry.id == entry_id,
                RosterEntry.course_id == course_id,
            )
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster entry not found")

    await db.delete(entry)
    await db.commit()
