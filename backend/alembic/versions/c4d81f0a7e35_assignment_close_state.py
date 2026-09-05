"""assignment close state: solution reveal flag and deadline finalization

Revision ID: c4d81f0a7e35
Revises: b18e4726f9cd
Create Date: 2026-09-04 22:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d81f0a7e35"
down_revision: str | None = "b18e4726f9cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Opt-in, per assignment: may students see reference solutions once the
    # assignment has closed? Defaults to off so existing rows keep the
    # "solutions never leave the backend" behaviour.
    op.add_column(
        "assignments",
        sa.Column(
            "reveal_solutions_after_close",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    # Deliberately separate from submitted_at: an assignment that closed on its
    # deadline is final, but the student never pressed Submit. Reusing
    # submitted_at would report submissions that never happened.
    op.add_column(
        "student_assignments",
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: anything already submitted was finalized at submit time.
    op.execute(
        "UPDATE student_assignments "
        "SET finalized_at = submitted_at "
        "WHERE submitted_at IS NOT NULL AND finalized_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("student_assignments", "finalized_at")
    op.drop_column("assignments", "reveal_solutions_after_close")
