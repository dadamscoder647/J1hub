# Release Checklist

Use this checklist before each production release.

## 1) Database migrations
- [ ] Confirm all model changes have matching Alembic migrations under `migrations/versions/`.
- [ ] Run `flask db upgrade` against a staging-like database.
- [ ] Verify `flask db check` reports no pending migration changes.

## 2) Secrets and environment safety
- [ ] Ensure `APP_ENV=production` is set in production.
- [ ] Verify required secrets are configured (`SECRET_KEY`, `JWT_SECRET_KEY`).
- [ ] If billing is enabled, verify both `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are set.

## 3) Webhook security
- [ ] Confirm Stripe webhook endpoint uses the current `STRIPE_WEBHOOK_SECRET`.
- [ ] Re-send a test webhook event and verify signature validation passes.

## 4) CORS policy
- [ ] Validate `ORIGINS` is restricted to trusted frontend domains (never wildcard in production).
- [ ] Confirm browser requests from allowed and disallowed origins behave as expected.

## 5) Rate limiting backend
- [ ] Verify `RATELIMIT_STORAGE_URI` points to a shared backend (e.g., Redis) for multi-instance deployments.
- [ ] Confirm rate-limit headers are enabled and visible in responses.
- [ ] Smoke test that burst traffic receives HTTP 429 responses.
