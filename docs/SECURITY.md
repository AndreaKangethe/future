# Security

JWT access tokens and Argon2 password hashing protect authentication. RBAC is
represented by `roles` and the composite `user_roles` assignment table; the
legacy `users.role` value remains a compatibility fallback while assignments
are migrated. Use `app.api.dependencies.require_role("admin")` on new
protected routes. The bootstrap process creates (or reuses) the configured
administrator and idempotently assigns the `admin` role.

Append-only audit events, encrypted integration secrets, rate limits, strict
CORS, and security headers remain required platform controls. Development
credentials are supplied only through `.env`.
