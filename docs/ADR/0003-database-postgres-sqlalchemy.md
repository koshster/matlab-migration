# ADR 0003 — Database: PostgreSQL 16 + SQLAlchemy 2.0 + Alembic

**Status:** Accepted

## Decision
Use PostgreSQL 16 as the database, SQLAlchemy 2.0 (async) as the ORM, and Alembic for migrations.

## Reason
Relational data with auditability requirements for grades. PostgreSQL provides `uuid`, `timestamptz`, `citext`, `jsonb` (for `params` and `saved_answers`), and row-level security. Alembic gives a reproducible migration history; no manual DDL allowed.

## Consequences
- Every schema change must have an Alembic migration committed alongside the model change.
- Seed script inserts one course, one 8-problem assignment, and one instructor account.
- The seed preserves `[3,3,4,4,5,5,6,6]` as `assignment_problems.params` JSON rows, not code.
