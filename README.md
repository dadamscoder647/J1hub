# J1Hub

J1Hub is a seasonal-workforce marketplace with worker, employer, and administrator workflows. The Flask API and React frontend cover account access, verification-document review, listings, applications, notifications, and Stripe billing.

## Local development

### Backend

Use Python 3.11 or later:

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

flask db upgrade
python scripts/seed_admin.py
python app.py
```

The API listens on `http://localhost:5000`. The seed script uses its documented local-only defaults in development and requires `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` in other environments. Public registration can create worker and employer accounts only; provision administrators through the seed script or another trusted operator process.

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

Verification uploads are stored beneath `UPLOAD_DIR`. The API enforces a size limit, permitted extension and MIME pairs, content signatures for PDF/PNG/JPEG, and path containment. `ALLOWED_UPLOAD_TYPES` can further restrict the MIME values in the built-in extension map.

Outside tests and the explicitly selected `DevelopmentConfig`, startup rejects `DEBUG`, an enabled `FLASK_DEBUG`, and an enabled Flask CLI debugger, and requires distinct Flask/JWT signing keys that are at least 32 characters; known checked-in placeholder, test-fixture, and CI key values are also rejected. Setting `APP_ENV=development` does not enable the local `DevelopmentConfig` exception. The direct `app.py` runner explicitly disables debug mode after dotenv loading. Generate separate random keys for local work; never reuse them in production. If Stripe is enabled, `STRIPE_WEBHOOK_SECRET` is required. Checkout also needs valid `PRICE_LISTING`, `PRICE_MONTHLY`, `BILLING_SUCCESS_URL`, and `BILLING_CANCEL_URL` values. The success/cancel URLs should point to `/billing/success` and `/billing/cancel` on the frontend.

For local Stripe testing, use test-mode Stripe credentials and the webhook signing secret from the local Stripe CLI. The webhook validates the signature and records event IDs so a retry does not grant credits twice. No live Stripe action is part of local setup or CI.

## Database migrations

```bash
export FLASK_APP='app:create_app'
flask db heads
flask db upgrade
flask db check
```

The current migration graph should have one head. The PostgreSQL CI job upgrades a clean database and checks model/schema parity; it also upgrades a database seeded at the previous mainline head and verifies that a stored verification document survives. Take a database backup before production migrations. The legacy visa-document conversion preserves existing rows, and the unique-application migration stops with an actionable error if duplicate records need operator review.

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
