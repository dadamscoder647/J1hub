# J1Hub

J1Hub is a seasonal-workforce marketplace with worker, employer, and administrator workflows. The Flask API and React frontend cover account access, verification-document review, listings, applications, notifications, and Stripe billing.

## Local development

### Backend

Use Python 3.12, the version pinned for local development and CI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt

export APP_ENV=development
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DATABASE_URL='sqlite:///app.db'
export UPLOAD_DIR='workspace/uploads'
export ORIGINS='http://localhost:5173'
export FLASK_APP='app:create_app'
export SEED_ADMIN_EMAIL='admin@example.com'
export SEED_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

flask db upgrade
python scripts/seed_admin.py
python app.py
```

The development runner listens on port `5000` and binds to `0.0.0.0`, so it may be reachable from other devices on the host's network. Seed scripts require explicit non-empty credentials in every environment. `seed_admin.py` uses `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`; it can create an administrator or reset the password and role of an account matching that email on the database selected by `DATABASE_URL`, so verify the target before running it. `seed_demo_data.py` also requires the employer and worker email/password variables; `bootstrap_demo.py` requires all six `SEED_ADMIN_*`, `SEED_EMPLOYER_*`, and `SEED_WORKER_*` values. These demo scripts update matching users and records, so run them only against a disposable local database. Public registration can create worker and employer accounts only; provision administrators through the seed script or another trusted operator process.

### Frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

The Vite app listens on `http://localhost:5173`. Its API base defaults to `http://localhost:5000/api/v1`; set `VITE_API_BASE_URL` only when the API is hosted elsewhere. The backend's `ORIGINS` value must include the frontend origin.

## API contract

The canonical API prefix is `/api/v1`. The checked-in OpenAPI contract is [openapi.yaml](openapi.yaml). Legacy unversioned aliases are enabled by `API_ENABLE_LEGACY_ROUTES=true` by default and can be disabled after clients have migrated. Legacy administrator verification routes return a deprecation `Warning` header.

Important endpoint groups:

- `/api/v1/auth`: register, login, and profile access.
- `/api/v1/verify`: worker uploads/status and administrator document downloads.
- `/api/v1/admin/verify`: administrator pending queue, approval, and rejection.
- `/api/v1/listings`: search, publish, update, favorites, applications, and application status.
- `/api/v1/billing`: checkout, current entitlements, billing history, and Stripe webhooks.
- `/api/v1/notifications`: the authenticated user's notifications.

Verification review and listing search are paginated. A pending queue response has `results`, `count`, and a `pagination` object. Workers need approved verification before they can apply, and an application is accepted only once per worker/listing pair. Employers can review applications only for listings they own.

## Uploads and security configuration

Verification uploads are stored beneath `UPLOAD_DIR`. The API enforces a size limit, permitted extension and MIME pairs, content signatures for PDF/PNG/JPEG, and path containment. `MAX_UPLOAD_SIZE` (bytes; 10 MiB by default) sets the per-file limit; `MAX_CONTENT_LENGTH` is derived from it with multipart overhead and is not a separate environment setting. The legacy `ALLOWED_UPLOAD_TYPES` environment value can narrow the built-in MIME map. An empty or non-matching allowlist fails closed and returns an upload configuration error. `ALLOWED_UPLOAD_RULES` is an application configuration map, not an environment variable; the built-in map is used only when the key is omitted, while an empty or invalid explicit value fails closed.

Outside tests and the explicitly selected `DevelopmentConfig`, startup rejects `DEBUG`, an enabled `FLASK_DEBUG`, and an enabled Flask CLI debugger, and requires distinct Flask/JWT signing keys that are at least 32 characters; known checked-in placeholder, test-fixture, and CI key values are also rejected. Setting `APP_ENV=development` does not enable the local `DevelopmentConfig` exception. The direct `app.py` runner explicitly disables debug mode after dotenv loading. Generate separate random keys for local work; never reuse them in production. If Stripe is enabled, `STRIPE_WEBHOOK_SECRET` is required. Checkout also needs valid `PRICE_LISTING` and `PRICE_MONTHLY` values. Set `BILLING_SUCCESS_URL` and `BILLING_CANCEL_URL` explicitly, or set `FRONTEND_URL` to the deployed frontend base URL to derive `/billing/success?session_id={CHECKOUT_SESSION_ID}` and `/billing/cancel`. When `ORIGINS` is unset, `FRONTEND_URL` supplies the CORS origin; if both are unset, CORS falls back to `*`, so set an explicit origin in deployed environments.

## Render staging

The root `render.yaml` is a reviewable Blueprint proposal for a paid, single-instance staging API, private PostgreSQL 16 database, persistent upload disk, and static React frontend. It tracks `main`, runs Alembic before startup, and disables per-service auto-deploys. The API normalizes Render's `postgresql://` URL and the legacy `postgres://` alias to `postgresql+psycopg://`. The first explicit Blueprint apply still provisions resources and starts an initial deployment. After linking, set Blueprint Auto Sync to No before future branch updates. Review the proposed monthly cost and operational limits before provisioning. Do not add Stripe keys to the Blueprint; configure test-mode values in Render only after staging is approved.

For local Stripe testing, use test-mode Stripe credentials and the webhook signing secret from the local Stripe CLI. The webhook validates the signature and records event IDs so a retry does not grant credits twice. Successful checkout and `invoice.paid` events activate or extend the recorded paid period. Cancellation or failed payment does not remove access before `active_until`; access expires when that timestamp passes without a successful renewal. No live Stripe action is part of local setup or CI.

## Database migrations

```bash
export FLASK_APP='app:create_app'
flask db heads
flask db history
flask db current
flask db upgrade
flask db check
```

After changing a model, generate a migration with `flask db migrate -m "describe schema change"`, then review the generated revision for correctness and data preservation before applying it. Do not run `flask db init` in this checkout; its migration metadata and history are already present.

The current migration graph should have one head. The PostgreSQL CI job upgrades a clean database and checks model/schema parity; it also upgrades a database seeded at a previous migration state and verifies that a stored verification document survives. Take a database backup before production migrations. The corrected visa-document conversion preserves rows when revision `d4d19a25492d` is applied from an earlier revision; a database that already recorded that revision as applied will not rerun the corrected code. Inspect the deployed Alembic revision and recover affected data from a backup or export if needed. The unique-application migration stops with an actionable error if duplicate records need operator review.

## Checks

From the repository root:

```bash
pytest -q
ruff check .
mypy --ignore-missing-imports --follow-imports skip app.py config.py
./scripts/check_openapi_sync.sh origin/main
```

For the frontend:

```bash
cd frontend
npm ci
npm run build
npm run test:e2e
```

The Playwright smoke tests stub the API to check worker, employer, and administrator interface flows. They do not replace a live staging exercise against a configured Stripe account or deployed storage service.
