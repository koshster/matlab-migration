"""phase_b_schema

Revision ID: b18e4726f9cd
Revises: a79abc08abaa
Create Date: 2026-08-23 21:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b18e4726f9cd"
down_revision: str | None = "a79abc08abaa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update courses table
    op.add_column(
        "courses", sa.Column("section", sa.String(length=32), server_default="001", nullable=False)
    )
    op.add_column(
        "courses", sa.Column("title", sa.String(length=255), server_default="", nullable=False)
    )
    op.add_column(
        "courses", sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False)
    )

    # 2. Create course_instructors table
    op.create_table(
        "course_instructors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("instructor_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="ta", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instructor_id"], ["instructors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "instructor_id", name="uq_course_instructor"),
    )

    # 3. Create roster_entries table
    op.create_table(
        "roster_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=True),
        sa.Column("pid", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="invited", nullable=False),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roster_entries_pid"), "roster_entries", ["pid"], unique=False)
    op.create_index(op.f("ix_roster_entries_email"), "roster_entries", ["email"], unique=False)

    # 4. Update assignments table
    op.add_column(
        "assignments",
        sa.Column("instructions", sa.String(length=2048), server_default="", nullable=False),
    )
    op.add_column(
        "assignments",
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "assignments",
        sa.Column("audience", sa.String(length=32), server_default="all", nullable=False),
    )
    op.add_column("assignments", sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True))

    # 5. Create assignment_targets table
    op.create_table(
        "assignment_targets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("roster_entry_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roster_entry_id"], ["roster_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "roster_entry_id", name="uq_assignment_roster_target"),
    )

    # 6. Update assignment_problems table
    op.add_column(
        "assignment_problems", sa.Column("points", sa.Float(), server_default="1.0", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("assignment_problems", "points")
    op.drop_table("assignment_targets")
    op.drop_column("assignments", "opens_at")
    op.drop_column("assignments", "audience")
    op.drop_column("assignments", "is_published")
    op.drop_column("assignments", "instructions")
    op.drop_index(op.f("ix_roster_entries_email"), table_name="roster_entries")
    op.drop_index(op.f("ix_roster_entries_pid"), table_name="roster_entries")
    op.drop_table("roster_entries")
    op.drop_table("course_instructors")
    op.drop_column("courses", "is_archived")
    op.drop_column("courses", "title")
    op.drop_column("courses", "section")
