# ADR 0009 — Instructor Auth: Email + Argon2id + httpOnly JWT Cookie

**Status:** Accepted

## Decision
Instructors authenticate via email + password. Passwords are hashed with Argon2id. Sessions use a JWT stored in an httpOnly, SameSite=Lax, Secure cookie. CSRF token required on mutations.

## Reason
Instructors access grade data and can override scores — real authentication is required. Argon2id is the current OWASP-recommended password hashing algorithm. httpOnly cookies prevent XSS-based token theft. Students and instructors use separate cookie names and separate dependency guards.

## Consequences
- An instructor cookie must never satisfy a student route, and vice versa.
- Login rate-limited to prevent brute force.
- `POST /auth/admin/logout` clears the cookie server-side.
- RBAC: `require_instructor(role=...)` dependency on all admin routes.
