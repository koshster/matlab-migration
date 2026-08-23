"""Canonical forms for the two identifiers people are looked up by.

Lives here rather than in a service because both auth and (in Phase D) roster
invitation matching must agree byte-for-byte: a roster entry Marko pastes as
"  A1234567 " has to match the PID a student later types as "a1234567", or the
invite silently never links.

Deliberately not using pydantic's EmailStr — that pulls in `email-validator`,
and standing rule #8 wants an ADR for a new dependency. If we start actually
sending mail, that dependency earns its ADR and this check should be replaced.
"""


def normalize_pid(pid: str) -> str:
    """Uppercase and strip. UCSD PIDs are case-insensitive in practice."""
    return pid.strip().upper()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def looks_like_email(value: str) -> bool:
    """Structural sanity check, not RFC validation.

    Rejects the mistakes that actually happen — blank, no `@`, no dot in the
    domain, stray whitespace — without pretending to be a real parser.
    """
    candidate = value.strip()
    if not candidate or any(c.isspace() for c in candidate):
        return False
    local, sep, domain = candidate.rpartition("@")
    if not sep or not local or not domain:
        return False
    return "." in domain and not domain.startswith(".") and not domain.endswith(".")
