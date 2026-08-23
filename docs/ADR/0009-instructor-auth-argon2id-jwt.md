# ADR 0009 — Instructor Auth: Email + Argon2id + httpOnly JWT Cookie

**Status:** Accepted (amended — see Amendments)

## Decision
Instructors authenticate via email + password. Passwords are hashed with Argon2id. Sessions use a JWT stored in an httpOnly, SameSite=Lax, Secure cookie. CSRF token required on mutations.

## Reason
Instructors access grade data and can override scores — real authentication is required. Argon2id is the current OWASP-recommended password hashing algorithm. httpOnly cookies prevent XSS-based token theft. Students and instructors use separate cookie names and separate dependency guards.

## Consequences
- An instructor cookie must never satisfy a student route, and vice versa.
- Login rate-limited to prevent brute force.
- `POST /auth/instructor/logout` clears the cookie server-side.
- RBAC: `require_instructor` / `require_course_role(course_id, minimum=...)` dependency on all admin routes.

## Amendments

### Route prefix is `/auth/instructor/*`, not `/auth/admin/*`
The original ADR specified `/auth/admin/*`, but that was never implemented, and the admin UI (`frontend/src/admin/AuthPage.tsx`, `InstructorContext`) was built against `/auth/instructor/*`. Implemented as `/auth/instructor/{register,login,logout,me}` to match the existing client rather than churn working UI. "Instructor" is also the more accurate noun — the table is `instructors`, and TAs are instructors with a lesser course role.

### Cookie separation is enforced by a `typ` claim, not just the cookie name
Separate cookie names alone are not an authorization boundary: the same token replayed under the other cookie name would have been accepted, because the payload carried only `sub` and `exp`. Tokens now carry `typ: "student" | "instructor"`, and each guard verifies it. Tokens minted before the claim existed are rejected rather than assumed to be student tokens — the only cost is re-login. Covered by `backend/tests/test_auth_guards.py` and `test_auth_api.py` in both directions.

### `Secure` is environment-driven
`secure` was hardcoded `False`. It is now `settings.session_cookie_secure`, which defaults to `False` only when `ENVIRONMENT=development` and can be overridden by `COOKIE_SECURE`.

### Course-scoped RBAC is staged
`require_course_role` resolves membership through `courses.instructor_id` (a single owner per course) until the `course_instructors(course_id, instructor_id, role)` junction lands. `app/services/authz.py::_load_role` is the only place that needs to change; route signatures and callers are already in their final shape. Roles are ordered `reader < ta < instructor < owner`. No-access returns 404 rather than 403 so instructors cannot enumerate other courses' ids.

### Not yet implemented
CSRF tokens on mutations and login rate limiting are still outstanding — both belong with Phase 8 hardening, and neither is a blocker for the admin dashboard behind a same-site cookie. Tracked in `docs/OPEN_QUESTIONS.md`.
