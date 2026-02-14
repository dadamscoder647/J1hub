# J1hub

Flask backend for J1hub.

## Required environment variables

For non-testing deployments (`TESTING=false`), the app now enforces secure secret configuration at startup.

Set the following variables before running in production-like environments:

- `SECRET_KEY` (required): Flask session/app secret. Must not be default placeholders like `change-me`.
- `JWT_SECRET_KEY` (required): JWT signing key. Must not be default placeholders like `change-me`.

## Optional environment variables

- `TESTING` (default: `false`): When `true`, secret placeholder checks are relaxed for test runs.
- `DEBUG` (default: `false`): Development-safe mode; strict secret enforcement is relaxed.
- `FLASK_ENV` / `ENV` (default: `production`): If set to `development`, strict secret enforcement is relaxed.
- `DATABASE_URL` (default: `sqlite:///app.db`)
- `UPLOAD_DIR` (default: `workspace/uploads`)
- `MAX_UPLOAD_SIZE` (default: `10485760`)
- `ALLOWED_UPLOAD_TYPES` (default: `image/jpeg,image/png,application/pdf`)
- `ORIGINS` (default: `*`)
- `RATE_LIMIT` (default: `60 per minute`)
- `RATELIMIT_STORAGE_URI` (default: `memory://`)
- `RATELIMIT_KEY_PREFIX` (optional)
- Stripe/billing keys:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `PRICE_LISTING`
  - `PRICE_MONTHLY`
  - `BILLING_SUCCESS_URL`
  - `BILLING_CANCEL_URL`

## Quick start

```bash
export SECRET_KEY='replace-with-long-random-secret'
export JWT_SECRET_KEY='replace-with-different-long-random-secret'
python app.py
```
