# J1Hub

J1Hub is a seasonal-workforce marketplace with worker, employer, and administrator workflows. The Flask API and React frontend cover account access, verification-document review, listings, applications, notifications, and Stripe billing.

## Project layout

| Path | Purpose |
|---|---|
| `app.py`, `config.py` | Flask application factory, extension and route setup, environment-backed configuration, and error handling. |
| `routes/` | Authentication, verification, listings/applications, billing, and notification API endpoints. |
| `models/` | SQLAlchemy records for users, listings, applications, verification documents, subscriptions, billing events, and notifications. |
| `services/`, `storage/` | Notification creation and the local document-storage implementation behind the storage interface. |
| `migrations/` | Alembic environment and the checked-in database revision history. |
| `frontend/` | React, TypeScript, and Vite client with worker, employer, and administrator screens. |
| `scripts/` | Explicit-credential seed tools and migration, OpenAPI, and Render Blueprint checks. |
| `tests/` | Backend API/domain tests; `frontend/e2e/` contains the Playwright smoke suite. |
| `openapi.yaml`, `docs/` | API contract, frontend billing integration notes, and release checklist. |

## User workflows

| Role | Main workflow |
|---|---|
| Worker | Register and sign in, submit verification documents, check review status, find listings, and apply after verification is approved. |
| Employer | Register and sign in, arrange listing credits or a subscription, create and manage listings, and review applications to owned listings. |
| Administrator | Review verification documents, download submitted files, approve or reject documents, and carry out trusted operator tasks. Administrator accounts are not available through public registration. |

A worker needs approved verification before applying. The API accepts one application per worker for each listing. Employers may review applications only for listings they own; administrators can review across listings.

## Local development

The backend uses Python 3.12. Create a virtual environment and install the project dependencies from the repository root:

    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt -r requirements-dev.txt
    cp .env.example .env

Edit the copied environment file before starting the application. Replace the signing-key placeholders with separate, randomly generated values of at least 32 characters. The Flask CLI can load .env through python-dotenv, which is included in requirements.txt. The direct python app.py runner does not load .env; export those values first if you use that runner. For example, run this command twice and use a different result for each key:

    python -c 'import secrets; print(secrets.token_urlsafe(32))'

The application requires distinct values for SECRET_KEY and JWT_SECRET_KEY outside tests and the explicitly selected DevelopmentConfig. APP_ENV=development is only an environment label; it does not select DevelopmentConfig or bypass the key checks. Do not commit .env.

The example file includes Stripe placeholders and example return URLs. Replace them with valid test-mode credentials, test Price IDs, a signing secret, and appropriate return URLs only when intentionally configuring local billing; otherwise, do not call billing routes with the placeholders. If STRIPE_SECRET_KEY is set, STRIPE_WEBHOOK_SECRET is also required. Never put production credentials in local examples.

Set Flask’s application factory, apply the checked-in migrations, and start the backend on loopback for local work:

    export FLASK_APP=app:create_app
    flask db upgrade
    flask run --host=127.0.0.1 --port=5000

The direct python app.py runner binds to 0.0.0.0 and may be reachable by other devices on the host’s network. Use it only when that exposure is intended.

In a second terminal, start the frontend:

    cd frontend
    cp .env.example .env.local
    npm ci
    npm run dev

The Vite frontend uses http://localhost:5173 and defaults its API base to http://localhost:5000/api/v1. Set the backend ORIGINS value to include the frontend origin.

## API

The canonical API prefix is /api/v1. The OpenAPI contract is in openapi.yaml. Use versioned routes for new clients. Unversioned compatibility routes are enabled by API_ENABLE_LEGACY_ROUTES=true by default and can be disabled after clients have migrated. Legacy administrator verification aliases are deprecated and return a Warning header.

| Area | Selected canonical routes |
|---|---|
| Health | GET /api/v1/health |
| Authentication | POST /api/v1/auth/register, POST /api/v1/auth/login, GET or PATCH /api/v1/auth/me |
| Worker verification | POST /api/v1/verify/upload, GET /api/v1/verify/status |
| Administrator verification | GET /api/v1/admin/verify/pending, POST /api/v1/admin/verify/{document_id}/approve, POST /api/v1/admin/verify/{document_id}/reject, GET /api/v1/verify/doc/{document_id} to download a file |
| Listings and applications | GET or POST /api/v1/listings, GET or PATCH /api/v1/listings/{listing_id}, GET /api/v1/listings/mine, POST /api/v1/listings/{listing_id}/apply, GET /api/v1/listings/{listing_id}/applications, GET /api/v1/listings/applications/mine, PATCH /api/v1/listings/{listing_id}/applications/{application_id} |
| Saved listings | GET /api/v1/listings/favorites, POST or DELETE /api/v1/listings/{listing_id}/favorite |
| Billing | GET /api/v1/billing/status, GET /api/v1/billing/history, POST /api/v1/billing/create-checkout-session, POST /api/v1/billing/webhook |
| Notifications | GET /api/v1/notifications, POST /api/v1/notifications/{notification_id}/read |

Search listings with category, q, city, active, page, and per_page query parameters. Listing search, the administrator pending queue, and the authenticated notifications list return results, count, and pagination metadata. Notification listing defaults to 20 items per page and caps per_page at 100.

### Register and sign in

Replace the sample email and password before sending the request. Public registration accepts worker or employer roles; it cannot create an administrator.

    BASE_URL=http://127.0.0.1:5000/api/v1

    curl -sS -X POST "$BASE_URL/auth/register" \
      -H "Content-Type: application/json" \
      -d '{"email":"worker@example.com","password":"replace-with-a-local-password","role":"worker"}'

Log in to obtain a bearer token for protected routes:

    curl -sS -X POST "$BASE_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"email":"worker@example.com","password":"replace-with-the-same-password"}'

The response contains `access_token` and the user profile. Copy the token from each account’s login response into the matching shell variable, such as `WORKER_TOKEN` or `EMPLOYER_TOKEN`, and send it as `Authorization: Bearer <token>`. `ADMIN_TOKEN` must come from a pre-provisioned administrator account; public registration accepts worker and employer roles only. For local admin access, use the seed-admin script only after confirming `DATABASE_URL` points to the intended disposable database. It can create an administrator or change the role and password of a matching account.

### Search and apply to a listing

    curl -sS "$BASE_URL/listings?category=job&city=Madison&active=true&page=1&per_page=20"

Applications require an authenticated worker whose verification has been approved:

    curl -sS -X POST "$BASE_URL/listings/1/apply" \
      -H "Authorization: Bearer $WORKER_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"message":"I am interested in this role."}'

The response is 409 if that worker has already applied to the listing.

### Upload a verification document

The document and waiver form field are required. The authenticated user must have the worker role.

    curl -sS -X POST "$BASE_URL/verify/upload" \
      -H "Authorization: Bearer $WORKER_TOKEN" \
      -F "document=@/path/to/verification-document.pdf" \
      -F "waiver=true"

Check status with `GET /api/v1/verify/status`. The administrator queue is paginated:

    curl -sS "$BASE_URL/admin/verify/pending?page=1&per_page=20" \
      -H "Authorization: Bearer $ADMIN_TOKEN"

Download the submitted file before reviewing it:

    curl -fS "$BASE_URL/verify/doc/1" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      --output verification-document.bin

Approve or reject the document after review:

    curl -sS -X POST "$BASE_URL/admin/verify/1/approve" \
      -H "Authorization: Bearer $ADMIN_TOKEN"

    curl -sS -X POST "$BASE_URL/admin/verify/1/reject" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"review_note":"Please upload a clearer copy."}'

### Employer listing and billing

An employer can create a listing only with an active subscription or available listing credit. The example below is for a test environment only. Creating a checkout session contacts Stripe; use test-mode credentials and test Price IDs. For local test billing, set `STRIPE_SECRET_KEY`, the applicable test Price ID (`PRICE_LISTING` or `PRICE_MONTHLY`), and valid `BILLING_SUCCESS_URL` and `BILLING_CANCEL_URL` values, or set `FRONTEND_URL` so the app can derive them. The copied `.env.example` contains placeholder billing values and explicit example return URLs; replace those URLs or clear both overrides when `FRONTEND_URL` is set. Clearing them without `FRONTEND_URL` leaves the return URLs unset, and checkout returns an error. If `STRIPE_SECRET_KEY` is set, the app also requires `STRIPE_WEBHOOK_SECRET`.

The webhook endpoint `/api/v1/billing/webhook` verifies Stripe signatures. A local server is not publicly reachable by Stripe, so forward test events to it with a local webhook forwarder or tunnel and configure the signing secret supplied by that forwarder. For a deployed test environment, configure the Stripe test-mode webhook with that service URL and use its endpoint signing secret. Keep credentials out of source control and never use live Stripe without separate approval. See [`docs/frontend_billing_integration.md`](docs/frontend_billing_integration.md) for billing status/history response fields.

    curl -sS -X POST "$BASE_URL/billing/create-checkout-session" \
      -H "Authorization: Bearer $EMPLOYER_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"purchase_type":"listing","quantity":1}'

The response contains sessionId and a hosted checkout URL. After credits or an active subscription are recorded, an employer can create a listing:

    curl -sS -X POST "$BASE_URL/listings" \
      -H "Authorization: Bearer $EMPLOYER_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"category":"job","title":"Seasonal Server","description":"Seasonal restaurant role.","contact_method":"email","contact_value":"hiring@example.com","company_name":"Example Resort","location_city":"Wisconsin Dells"}'

Billing status and history are available to authenticated employers and administrators. The webhook validates Stripe signatures and uses event IDs to prevent duplicate processing. Cancellation or a late/failed renewal does not remove access before the recorded paid period ends; access expires after that period if renewal has not succeeded.

## Configuration and upload rules

- SECRET_KEY and JWT_SECRET_KEY must be distinct random values at least 32 characters long outside tests and the explicit DevelopmentConfig.
- DATABASE_URL selects the database. PostgreSQL URLs using postgres:// or postgresql:// are normalized to the Psycopg 3 driver.
- UPLOAD_DIR selects local document storage. MAX_UPLOAD_SIZE is the per-file limit, 10 MiB by default. The request-size ceiling is derived from it with multipart overhead; MAX_CONTENT_LENGTH is not a separate environment variable.
- Uploads require a permitted extension/MIME pair, a recognized content signature for PDF/PNG/JPEG, and a path contained under UPLOAD_DIR. ALLOWED_UPLOAD_TYPES is a comma-separated MIME allowlist that narrows the built-in MIME map; it does not accept extension-only tokens such as pdf or png. Empty or non-matching upload configuration fails closed. ALLOWED_UPLOAD_RULES is a programmatic extension-to-MIME map, not an environment variable.
- Set ORIGINS to the exact frontend origins. FRONTEND_URL supplies the CORS origin and success/cancel URL defaults when the explicit settings are unset. The copied .env.example has explicit example billing return URLs; replace or blank them if you want URLs derived from FRONTEND_URL. If ORIGINS and FRONTEND_URL are both unset, the CORS fallback is wildcard; do not use that fallback for a deployed environment.
- RATE_LIMIT defaults to 60 per minute. RATELIMIT_STORAGE_URI defaults to memory://. RATELIMIT_KEY_PREFIX defaults to j1hub: outside tests; set an explicit prefix if deployment environments share a rate-limit store and should have separate counters.

### Owner decisions before staging

The repository’s render.yaml is a review-only proposal. Applying it provisions the configured API, PostgreSQL database, persistent upload disk, and static frontend, then starts an initial deployment. Confirm current plan charges and review the resource footprint in Render before applying; this draft does not estimate cost. Service auto-deploy is off, but Blueprint Auto Sync is separate; set it to No before later branch updates. Keep Stripe values out of the Blueprint and add approved test-mode values only after staging is authorized.

For a fresh deployment using the proposed Render Blueprint, leave `ALLOWED_UPLOAD_TYPES` unset so the built-in MIME allowlist applies. The setting accepts MIME types only; extension-only values such as `pdf,png` are unsupported and fail closed. Before migrating a separately configured service, inspect its current value and replace extension tokens with intended MIME values or unset the variable. Do not add extension-token compatibility without reviewing the content-signature checks.

If the uniqueness migration finds duplicate worker/listing applications, it stops for operator review. Resolve any existing duplicates deliberately; do not automatically delete application records.

## Troubleshooting

- **Startup reports invalid signing keys:** set separate, random `SECRET_KEY` and `JWT_SECRET_KEY` values of at least 32 characters. `APP_ENV=development` labels the environment; it does not select `DevelopmentConfig`. The Flask CLI can load `.env`; the direct `python app.py` runner requires exported variables.
- **Browser requests fail CORS checks:** set `ORIGINS` to the exact frontend origin. A wildcard fallback is available only when both `ORIGINS` and `FRONTEND_URL` are unset; do not rely on it for deployment.
- **A verification upload is rejected:** check the per-file size and confirm that the extension, recognized file signature, and any declared MIME type match an allowed PDF, PNG, or JPEG. `ALLOWED_UPLOAD_TYPES` accepts MIME values only; extension-only values such as `pdf` or `png` do not work.
- **A database command reports an unexpected revision or duplicate application rows:** first confirm `DATABASE_URL` targets the intended database, then inspect `flask db current`, `flask db history`, and `flask db heads`. Apply checked-in revisions with `flask db upgrade`; do not run `flask db init`. The application uniqueness migration stops for manual review if duplicate worker/listing rows exist.
- **Checkout or webhook setup fails:** see [Employer listing and billing](#employer-listing-and-billing) for test-mode keys, Price IDs, return URLs, and local event forwarding. Confirm the webhook signing secret matches the endpoint or local forwarder; never disable signature validation to make a request pass.
- **The health route succeeds but API data is unavailable:** `GET /api/v1/health` reports process health only. Check the API logs and the `X-Request-ID` response header while investigating database connectivity.

## Database and release operations

Inspect migration state and apply the checked-in migration graph:

    export FLASK_APP=app:create_app
    flask db heads
    flask db history
    flask db current
    flask db upgrade
    flask db check

The repository already contains Alembic history; do not run flask db init. After a model change, generate a migration with flask db migrate, inspect the revision for correctness and data preservation, then test it against an appropriate database before applying it. Take a database backup before production migrations. The visa-document migration preserves rows when applied from an earlier revision; an already-recorded revision will not rerun corrected migration code.

Before release, use docs/release-checklist.md. Confirm required keys, database migration state, webhook signature validation, restricted CORS origins, and rate-limit behavior. For multi-instance services, configure a shared rate-limit backend. Check X-Request-ID when correlating API errors.

Run the local backend checks from the repository root:

    pytest -q
    ruff check .
    mypy --ignore-missing-imports --follow-imports skip app.py config.py
    ./scripts/check_openapi_sync.sh origin/main

For the frontend:

    cd frontend
    npm ci
    npm run build
    npm run test:e2e

The Playwright smoke suite stubs API calls; it checks frontend behavior against those stubs, not a deployed browser/API path or real Stripe delivery. It also does not establish deployed persistent-file-storage or restore behavior.
