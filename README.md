# J1Hub API

J1Hub is a Flask-based backend API for managing J-1 community workflows: user authentication, worker verification document review, job/housing/gig listings, and employer billing via Stripe.

## Project purpose

This service is designed to:
- support role-based users (`worker`, `employer`, `admin`);
- let workers upload visa-related verification documents;
- let admins review and approve/reject verification;
- let employers/admins post listings and workers apply;
- enforce listing monetization through one-time credits or subscriptions.

## Architecture overview

### Core stack
- **Flask** application factory (`create_app`) with blueprint modules.
- **SQLAlchemy + Flask-Migrate/Alembic** for database models and schema migrations.
- **JWT auth** using `Flask-JWT-Extended`.
- **Rate limiting** with `Flask-Limiter`.
- **CORS** with `Flask-Cors`.
- **Stripe** API integration for billing checkout + webhook processing.

### App modules
- `app.py`: app factory, extension initialization, CORS/rate limit config, blueprint registration, health and error handlers.
- `config.py`: environment-based settings.
- `models/`: persistence layer (`User`, `Listing`, `Application`, `VisaDocument`, `EmployerSubscription`).
- `routes/`: API surface:
  - `routes/auth.py`
  - `routes/listings.py`
  - `routes/verify.py`
  - `routes/billing.py`
- `storage/local_storage.py`: upload persistence to local filesystem.
- `migrations/`: Alembic migration history.
- `tests/`: pytest test suite.

---

## Local setup

### 1) Prerequisites
- Python **3.11+** (CI uses 3.12)
- `pip`
- SQLite (default) or Postgres/MySQL via SQLAlchemy `DATABASE_URL`

### 2) Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Environment variables

Create a `.env` file (or export vars in your shell). At minimum:

```bash
# auth / app
SECRET_KEY=replace-me
JWT_SECRET_KEY=replace-me-too

# database
DATABASE_URL=sqlite:///app.db

# uploads
UPLOAD_DIR=workspace/uploads
MAX_UPLOAD_SIZE=10485760
ALLOWED_UPLOAD_TYPES=image/jpeg,image/png,application/pdf

# CORS + rate limit
ORIGINS=http://localhost:3000
RATE_LIMIT=60 per minute
RATELIMIT_STORAGE_URI=memory://
RATELIMIT_KEY_PREFIX=

# Stripe / billing
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
PRICE_LISTING=price_xxx
PRICE_MONTHLY=price_xxx
BILLING_SUCCESS_URL=http://localhost:3000/billing/success
BILLING_CANCEL_URL=http://localhost:3000/billing/cancel
```

### Required by area
- **Auth**: `SECRET_KEY`, `JWT_SECRET_KEY`
- **DB**: `DATABASE_URL`
- **Stripe billing**: `STRIPE_SECRET_KEY`, `PRICE_LISTING`, `PRICE_MONTHLY`, `BILLING_SUCCESS_URL`, `BILLING_CANCEL_URL` (and `STRIPE_WEBHOOK_SECRET` strongly recommended)
- **Uploads/verify**: `UPLOAD_DIR` (writeable), `MAX_UPLOAD_SIZE`, `ALLOWED_UPLOAD_TYPES`

---

## Database migrations

Set Flask app module:

```bash
export FLASK_APP=app:create_app
```

Run migrations:

```bash
flask db upgrade
```

Create a new migration after model changes:

```bash
flask db migrate -m "describe schema change"
flask db upgrade
```

If this is a brand-new DB and migration metadata has not been initialized:

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```

---

## Run commands

### Development
```bash
export FLASK_APP=app:create_app
flask run --host=0.0.0.0 --port=5000
```

### Production-style local run
```bash
gunicorn 'app:create_app()' --bind 0.0.0.0:5000 --workers 2
```

### Health check
```bash
curl http://localhost:5000/health
```

---

## API examples

Base URL:
```bash
BASE_URL=http://localhost:5000
```

### Auth
#### Register
```bash
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "worker@example.com",
    "password": "StrongPass123!",
    "role": "worker"
  }'
```

#### Login
```bash
curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "worker@example.com",
    "password": "StrongPass123!"
  }'
```

Store the returned token:
```bash
TOKEN="<access_token_from_login>"
```

### Listings
#### Search listings
```bash
curl "$BASE_URL/listings?category=job&q=server&city=miami&active=true"
```

#### Create listing (employer/admin token required)
```bash
curl -X POST "$BASE_URL/listings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "job",
    "title": "Restaurant Server",
    "description": "Seasonal role near downtown.",
    "company_name": "Beachside Grill",
    "contact_method": "email",
    "contact_value": "hiring@beachside.example",
    "location_city": "Miami",
    "pay_rate": "18.50",
    "currency": "USD",
    "shift": "evening",
    "is_public": true
  }'
```

#### Apply to listing (worker token required)
```bash
curl -X POST "$BASE_URL/listings/1/apply" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I am interested in this role."}'
```

### Verify
#### Upload verification document (multipart form)
```bash
curl -X POST "$BASE_URL/verify/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "document=@/path/to/visa-document.pdf" \
  -F "waiver=true"
```

#### Check verification status
```bash
curl -X GET "$BASE_URL/verify/status" \
  -H "Authorization: Bearer $TOKEN"
```

#### Admin: list pending docs
```bash
curl -X GET "$BASE_URL/admin/verify/pending" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Admin: approve/reject
```bash
curl -X POST "$BASE_URL/verify/12/approve" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl -X POST "$BASE_URL/verify/12/reject" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"review_note":"Document is unreadable."}'
```

### Billing
#### Create Stripe checkout session (listing credit)
```bash
curl -X POST "$BASE_URL/billing/create-checkout-session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purchase_type": "listing",
    "quantity": 3,
    "success_url": "http://localhost:3000/billing/success",
    "cancel_url": "http://localhost:3000/billing/cancel"
  }'
```

#### Create Stripe checkout session (subscription)
```bash
curl -X POST "$BASE_URL/billing/create-checkout-session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purchase_type": "subscription",
    "success_url": "http://localhost:3000/billing/success",
    "cancel_url": "http://localhost:3000/billing/cancel"
  }'
```

#### Stripe webhook endpoint
```bash
curl -X POST "$BASE_URL/billing/webhook" \
  -H "Stripe-Signature: <signature>" \
  -H "Content-Type: application/json" \
  -d '{"type":"checkout.session.completed","data":{"object":{"metadata":{"billing_type":"listing"}}}}'
```

> In production, send real signed webhooks from Stripe and set `STRIPE_WEBHOOK_SECRET`.

---

## Tests

Run the full test suite:

```bash
pytest -q
```

Optional coverage run:

```bash
pytest --cov=. --cov-report=term-missing
```

---

## Deployment and security notes

- Use a strong, unique `SECRET_KEY` and `JWT_SECRET_KEY` per environment.
- Do not run with default secrets in production.
- Back your `DATABASE_URL` with a managed database and regular backups.
- Store uploaded files in persistent object storage (e.g., S3) for production rather than local disk.
- Restrict `ORIGINS` to trusted frontend domains.
- Configure persistent rate-limit backend (Redis) via `RATELIMIT_STORAGE_URI`.
- Always set `STRIPE_WEBHOOK_SECRET` and verify webhook signatures.
- Terminate TLS at a load balancer/reverse proxy and enforce HTTPS.
- Run behind Gunicorn and a reverse proxy (Nginx/ALB/Cloud Run ingress).
- Keep dependencies patched and run CI tests before deploy.

## License

MIT (`LICENSE`).
