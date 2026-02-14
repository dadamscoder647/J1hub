# J1hub API

J1hub is a Flask-based backend for a J-1 exchange community marketplace. It provides user authentication, visa verification workflows, role-based listing access, and employer billing via Stripe.

## Overview

J1hub supports three main personas:

- **Worker**: registers, uploads visa documents, tracks verification status, discovers listings, and applies to listings.
- **Employer**: registers, purchases listing credits or a subscription, creates/manages listings, and receives worker applications.
- **Admin**: reviews visa documents, approves/rejects verification, downloads uploaded docs, and can perform elevated listing/billing actions.

Core business capabilities:

- JWT-based authentication and role-aware access control.
- Visa document upload/review lifecycle (`unverified -> pending -> approved/rejected`).
- Listings search + creation/update + worker application flow.
- Stripe checkout + webhook processing for listing credits/subscriptions.
- Operational hardening via CORS, rate limiting, structured JSON error responses, and health checks.

## Architecture

J1hub uses an application-factory Flask architecture:

- `create_app()` initializes extensions (`SQLAlchemy`, `Flask-Migrate`, `JWT`, CORS, rate limiter).
- Feature areas are separated into blueprints:
  - `routes/auth.py`
  - `routes/verify.py`
  - `routes/listings.py`
  - `routes/billing.py`
- SQLAlchemy models encapsulate persistence logic for users, listings, applications, verification docs, and subscriptions.
- File uploads are stored through a storage abstraction (`storage/local_storage.py`).
- Migrations are managed with Alembic under `migrations/`.

High-level request flow:

1. Request enters Flask app.
2. Rate limiter/CORS middleware apply.
3. Route handler validates payload and authorization.
4. Model/service logic executes and commits through SQLAlchemy.
5. Response (or standardized JSON error) returns with `X-Request-ID`.

## Tech Stack

- **Language**: Python 3
- **Web framework**: Flask
- **Auth**: Flask-JWT-Extended
- **ORM**: SQLAlchemy
- **Migrations**: Flask-Migrate / Alembic
- **Billing**: Stripe Python SDK
- **Cross-Origin support**: Flask-CORS
- **Rate limiting**: Flask-Limiter
- **App server (deployment)**: Gunicorn
- **Config/env loading**: `os.getenv` + `python-dotenv`
- **Testing**: pytest

## Folder Structure

```text
.
├── app.py                    # Flask app factory + extension wiring + health/errors
├── config.py                 # Environment-driven configuration
├── models/                   # SQLAlchemy models (User, Listing, VisaDocument, etc.)
├── routes/                   # API blueprints (auth, verify, listings, billing)
├── storage/                  # File storage abstraction and local implementation
├── utils/                    # Shared utilities (e.g. JSON request validation)
├── migrations/               # Alembic migration environment and versions
├── scripts/                  # Bootstrap/seed helper scripts
├── tests/                    # pytest test suite
├── postman/                  # API collection exports
└── requirements*.txt         # Runtime and dev dependencies
```

## Environment Variables (`config.py`)

The app reads configuration from environment variables. Defaults shown below are the effective fallback values in `Config`.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `change-me` | Flask secret key (sessions/signing). |
| `JWT_SECRET_KEY` | `SECRET_KEY` value | JWT signing key. |
| `DATABASE_URL` | `sqlite:///app.db` | SQLAlchemy DB connection URL. |
| `UPLOAD_DIR` | `workspace/uploads` | Base directory for uploaded verification documents. |
| `MAX_UPLOAD_SIZE` | `10485760` (10 MB) | Max upload file size in bytes. |
| `ALLOWED_UPLOAD_TYPES` | `image/jpeg,image/png,application/pdf` | Allowed upload MIME-like values (used for extension checks). |
| `ORIGINS` | `*` | CORS allow-list (`*` or comma-separated origins). |
| `RATE_LIMIT` | `60 per minute` | Global default rate limit. |
| `RATELIMIT_STORAGE_URI` | `memory://` | Backend for rate limit state. |
| `RATELIMIT_KEY_PREFIX` | `""` (empty) | Prefix for rate limit keys (auto-set per app instance if empty). |
| `STRIPE_SECRET_KEY` | `None` | Stripe API secret key (required for billing endpoints). |
| `STRIPE_WEBHOOK_SECRET` | `None` | Stripe webhook signing secret (recommended). |
| `PRICE_LISTING` | `None` | Stripe Price ID for listing-credit purchase. |
| `PRICE_MONTHLY` | `None` | Stripe Price ID for monthly subscription. |
| `BILLING_SUCCESS_URL` | `None` | Checkout success redirect URL. |
| `BILLING_CANCEL_URL` | `None` | Checkout cancel redirect URL. |

> Recommended: create a local `.env` and export values before running.

## Local Setup

### 1) Clone and enter project

```bash
git clone <your-repo-url>
cd J1hub
```

### 2) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
# Optional dev tooling
pip install -r requirements-dev.txt
```

### 4) Configure environment variables

Example:

```bash
export SECRET_KEY="dev-secret"
export JWT_SECRET_KEY="dev-jwt-secret"
export DATABASE_URL="sqlite:///app.db"
export UPLOAD_DIR="workspace/uploads"
export ORIGINS="http://localhost:3000"

# Billing (optional unless testing billing routes)
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export PRICE_LISTING="price_..."
export PRICE_MONTHLY="price_..."
export BILLING_SUCCESS_URL="http://localhost:3000/billing/success"
export BILLING_CANCEL_URL="http://localhost:3000/billing/cancel"
```

### 5) Run migrations

```bash
export FLASK_APP=app.py
flask db upgrade
```

### 6) Run the API server

```bash
python app.py
# or
flask run --host 0.0.0.0 --port 5000
```

Health check:

```bash
curl http://localhost:5000/health
```

## API Endpoint Catalog

Base URL (local): `http://localhost:5000`

### Auth

#### `POST /auth/register`
Register a new user.

Request:

```json
{
  "email": "worker@example.com",
  "password": "secret123",
  "role": "worker"
}
```

Success (`201`):

```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 1,
    "email": "worker@example.com",
    "role": "worker"
  }
}
```

#### `POST /auth/login`
Authenticate and get JWT.

Request:

```json
{
  "email": "worker@example.com",
  "password": "secret123"
}
```

Success (`200`):

```json
{
  "access_token": "<jwt>",
  "user": {
    "id": 1,
    "email": "worker@example.com",
    "role": "worker"
  }
}
```

---

### Verify

#### `POST /verify/upload` (JWT required)
Upload visa document via `multipart/form-data`.

Form fields:
- `document`: file (`.pdf`, `.jpg`, `.jpeg`, `.png`)
- `waiver`: boolean-like string (`true/false/1/0/yes/no`)

Success (`201`):

```json
{
  "id": 12,
  "status": "pending"
}
```

#### `GET /verify/status` (JWT required)
Get current user verification status and latest document metadata.

Success (`200`):

```json
{
  "verification_status": "pending",
  "latest_document": {
    "id": 12,
    "user_id": 1,
    "filename": "document.pdf",
    "file_path": "<stored-path>",
    "file_type": "application/pdf",
    "status": "pending",
    "reviewer_id": null,
    "review_note": null,
    "waiver_acknowledged": true,
    "created_at": "2025-01-01T12:00:00"
  }
}
```

#### `GET /verify/doc/<document_id>` (Admin JWT required)
Download stored verification document.

Success: binary file attachment.

#### `GET /admin/verify/pending` (Admin JWT required)
List pending documents in oldest-first order.

Success (`200`):

```json
[
  {
    "id": 12,
    "user_id": 1,
    "filename": "document.pdf",
    "created_at": "2025-01-01T12:00:00"
  }
]
```

#### `POST /verify/<document_id>/approve` (Admin JWT required)
Approve a document and mark user verified.

Success (`200`):

```json
{
  "id": 12,
  "status": "approved",
  "verification_status": "approved"
}
```

#### `POST /verify/<document_id>/reject` (Admin JWT required)
Reject a document with optional note.

Request (optional body):

```json
{
  "review_note": "Missing page 2"
}
```

Success (`200`):

```json
{
  "id": 12,
  "status": "rejected",
  "verification_status": "rejected",
  "review_note": "Missing page 2"
}
```

---

### Listings

#### `GET /listings`
Search/filter listings.

Supported query params:
- `category` (`job|housing|ride|gig`)
- `q` (free text over title/description/company)
- `city`
- `active` (`true/false`, defaults to `true`)

Success (`200`):

```json
{
  "results": [
    {
      "id": 101,
      "category": "job",
      "title": "Kitchen Assistant",
      "description": "Seasonal role",
      "company_name": "Resort Co",
      "contact_method": "email",
      "contact_value": "jobs@resortco.com",
      "location_city": "Wisconsin Dells",
      "pay_rate": 16.5,
      "currency": "USD",
      "shift": "Evening",
      "is_public": true,
      "is_active": true,
      "expires_at": null,
      "created_by": 22,
      "created_at": "2025-01-01T12:00:00"
    }
  ],
  "count": 1
}
```

#### `POST /listings` (Employer/Admin JWT required)
Create listing. Employers need active subscription or listing credits.

Request:

```json
{
  "category": "job",
  "title": "Kitchen Assistant",
  "description": "Seasonal role",
  "contact_method": "email",
  "contact_value": "jobs@resortco.com",
  "company_name": "Resort Co",
  "location_city": "Wisconsin Dells",
  "pay_rate": 16.5,
  "currency": "USD",
  "shift": "Evening",
  "is_public": true,
  "is_active": true,
  "expires_at": "2025-12-31T23:59:59Z"
}
```

Success (`201`): listing object.

Common error (`402`):

```json
{
  "error": "Listing credits or an active subscription is required to post listings."
}
```

#### `GET /listings/<listing_id>`
Get a listing if caller has access.

#### `PATCH /listings/<listing_id>` (Owner/Admin JWT required)
Partial update fields like `title`, `description`, `contact_*`, `is_public`, `is_active`, etc.

#### `POST /listings/<listing_id>/apply` (Worker JWT required)
Apply to a listing.

Request:

```json
{
  "message": "I am interested in this role and can start in June."
}
```

Success (`201`):

```json
{
  "id": 501,
  "user_id": 1,
  "listing_id": 101,
  "message": "I am interested in this role and can start in June.",
  "created_at": "2025-01-01T12:00:00"
}
```

---

### Billing

#### `POST /billing/create-checkout-session` (Employer/Admin JWT required)
Create Stripe Checkout session for listing credits or subscription.

Request for listing credits:

```json
{
  "purchase_type": "listing",
  "quantity": 3,
  "success_url": "http://localhost:3000/billing/success",
  "cancel_url": "http://localhost:3000/billing/cancel"
}
```

Request for subscription:

```json
{
  "purchase_type": "subscription",
  "success_url": "http://localhost:3000/billing/success",
  "cancel_url": "http://localhost:3000/billing/cancel"
}
```

Success (`200`):

```json
{
  "sessionId": "cs_test_...",
  "url": "https://checkout.stripe.com/..."
}
```

#### `POST /billing/webhook`
Stripe webhook endpoint for:
- `checkout.session.completed` (listing credits or subscription setup)
- `invoice.paid` (subscription renewal extension)

Success (`200`):

```json
{
  "status": "success"
}
```

## Role-based Workflow Walkthroughs

### Worker workflow

1. Register/login (`/auth/register`, `/auth/login`).
2. Upload visa document (`/verify/upload` with `waiver=true`).
3. Poll status (`/verify/status`) until approved.
4. Browse listings (`GET /listings`, optional filters).
5. Apply to eligible listing (`POST /listings/<id>/apply`).

### Employer workflow

1. Register/login as `employer`.
2. Create Stripe session (`/billing/create-checkout-session`) for listing credits or subscription.
3. Ensure webhook updates credits/subscription (`/billing/webhook`).
4. Create listing (`POST /listings`).
5. Update/manage listing visibility (`PATCH /listings/<id>`).

### Admin workflow

1. Login as `admin`.
2. Review pending docs (`GET /admin/verify/pending`).
3. Download doc (`GET /verify/doc/<id>`), then approve/reject.
4. Approved users can access restricted listing content/actions.
5. Admin can also create listings and start billing sessions if needed.

## Deployment Notes

### Runtime

- Production server can run with Gunicorn, e.g.:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

- Set strong production secrets (`SECRET_KEY`, `JWT_SECRET_KEY`).
- Configure a production DB via `DATABASE_URL` (PostgreSQL recommended).
- Persist `UPLOAD_DIR` on durable storage shared with app instances.
- Use a shared rate-limit storage backend (e.g., Redis via `RATELIMIT_STORAGE_URI`) when running multiple instances.

### Stripe webhook setup

- Point Stripe webhook URL to `https://<your-domain>/billing/webhook`.
- Subscribe to at least:
  - `checkout.session.completed`
  - `invoice.paid`
- Configure `STRIPE_WEBHOOK_SECRET` from Stripe endpoint signing secret.

### Operational checks

Run these checks after deploy:

```bash
# Health
curl -sS https://<your-domain>/health

# Auth smoke test
curl -sS -X POST https://<your-domain>/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@example.com","password":"secret123"}'

# Tail logs (example, adjust for your platform)
# docker logs -f <container>
# journalctl -u j1hub -f
```

What to monitor:

- `5xx` error rate and webhook failures.
- Rate-limit spikes (`429`) indicating abuse or misconfigured clients.
- Upload failures (size/type validation).
- Billing webhook delivery latency and success ratio.

## Quick cURL Examples

```bash
# 1) Register
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"worker@example.com","password":"secret123","role":"worker"}'

# 2) Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"worker@example.com","password":"secret123"}'

# 3) Search listings
curl "http://localhost:5000/listings?category=job&city=dells"
```
