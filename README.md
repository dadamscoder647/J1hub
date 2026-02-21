# J1Hub API

J1Hub is a Flask-based backend for a seasonal workforce marketplace. It supports:
- account registration/login with JWT auth,
- visa verification document uploads and admin review,
- listings discovery + posting workflows,
- Stripe-powered billing for listing credits and employer subscriptions.

## Tech stack
- Python 3.11+
- Flask + Flask blueprints
- SQLAlchemy + Flask-Migrate (Alembic)
- JWT via `flask-jwt-extended`
- Stripe Python SDK

---

## Local setup

### 1) Clone and install dependencies
```bash
git clone <your-repo-url>
cd J1hub
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2) Create environment file
Create a `.env` file (or export variables in your shell) with the required values below.

### 3) Initialize or migrate the database
```bash
export FLASK_APP=app:create_app
flask db upgrade
```

### 4) (Optional) Seed admin/demo data
```bash
python scripts/seed_admin.py
python scripts/seed_demo_data.py
```

### 5) Start the API
```bash
python app.py
```
By default, the service runs on `http://localhost:5000`.

---

## Required environment variables

### Core app
- `SECRET_KEY`: Flask secret key.
- `JWT_SECRET_KEY`: JWT signing key (defaults to `SECRET_KEY`, but set explicitly in non-dev environments).
- `DATABASE_URL`: SQLAlchemy DB URL (e.g. `sqlite:///app.db` or Postgres URL).
- `ORIGINS`: CORS origins (`*` or comma-separated list).

### Upload + verification
- `UPLOAD_DIR`: directory where uploaded verification files are stored.
- `MAX_UPLOAD_SIZE`: max upload size in bytes (default `10485760`).
- `ALLOWED_UPLOAD_TYPES`: comma-separated MIME/extensions accepted by verification upload (default includes jpg/png/pdf variants).

### Rate limiting
- `RATE_LIMIT`: e.g. `60 per minute`.
- `RATELIMIT_STORAGE_URI`: e.g. `memory://` for local, Redis URI for multi-instance deployments.
- `RATELIMIT_KEY_PREFIX`: optional stable prefix for distributed limit key namespaces.

### Billing + Stripe
- `STRIPE_SECRET_KEY`: Stripe secret API key.
- `STRIPE_WEBHOOK_SECRET`: webhook signing secret used to validate `/billing/webhook`.
- `PRICE_LISTING`: Stripe Price ID for one-time listing credits.
- `PRICE_MONTHLY`: Stripe Price ID for recurring subscription plan.
- `BILLING_SUCCESS_URL`: redirect URL after successful checkout.
- `BILLING_CANCEL_URL`: redirect URL after canceled checkout.

Example:
```bash
export SECRET_KEY="dev-secret"
export JWT_SECRET_KEY="dev-jwt-secret"
export DATABASE_URL="sqlite:///app.db"
export ORIGINS="http://localhost:3000"
export UPLOAD_DIR="workspace/uploads"
export MAX_UPLOAD_SIZE="10485760"
export ALLOWED_UPLOAD_TYPES="image/jpeg,image/png,application/pdf"
export RATE_LIMIT="60 per minute"
export RATELIMIT_STORAGE_URI="memory://"

export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export PRICE_LISTING="price_..."
export PRICE_MONTHLY="price_..."
export BILLING_SUCCESS_URL="http://localhost:3000/billing/success"
export BILLING_CANCEL_URL="http://localhost:3000/billing/cancel"
```

---

## Database migration commands

Use Flask-Migrate/Alembic via `flask db`:

```bash
export FLASK_APP=app:create_app

# apply migrations
flask db upgrade

# rollback one revision
flask db downgrade -1

# generate migration after model changes
flask db migrate -m "describe change"

# view migration history and heads
flask db history
flask db heads
flask db current
```

---

## Service startup steps (recommended dev flow)
1. Activate virtualenv.
2. Export env vars or load `.env`.
3. Run `flask db upgrade`.
4. Start server with `python app.py`.
5. Verify health endpoint:
   ```bash
   curl http://localhost:5000/health
   ```

---

## API usage guide

Base URL used in examples:
```bash
BASE_URL="http://localhost:5000"
```

### 1) `/auth` token flow

#### Register
```bash
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"worker@example.com",
    "password":"StrongPass123!",
    "role":"worker"
  }'
```

Representative response (`201`):
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 12,
    "email": "worker@example.com",
    "role": "worker"
  }
}
```

#### Login and capture token
```bash
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"worker@example.com",
    "password":"StrongPass123!"
  }' | python -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

echo "$TOKEN"
```

Representative response (`200`):
```json
{
  "access_token": "<jwt>",
  "user": {
    "id": 12,
    "email": "worker@example.com",
    "role": "worker"
  }
}
```

Use this header for protected endpoints:
```bash
-H "Authorization: Bearer $TOKEN"
```

---

### 2) `/listings`

#### List/search listings (public or authenticated)
```bash
curl -s "$BASE_URL/listings?category=job&city=madison&active=true"
```

Representative response (`200`):
```json
{
  "results": [
    {
      "id": 55,
      "category": "job",
      "title": "Kitchen Prep",
      "description": "Evening prep shift",
      "company_name": "North Lake Diner",
      "contact_method": null,
      "contact_value": null,
      "location_city": "Madison",
      "pay_rate": 17.5,
      "currency": "USD",
      "shift": "evening",
      "is_public": true,
      "is_active": true,
      "expires_at": null,
      "created_by": 8,
      "created_at": "2026-01-14T20:11:32.112233"
    }
  ],
  "count": 1
}
```

#### Create listing (employer/admin, requires token + credits/subscription)
```bash
curl -s -X POST "$BASE_URL/listings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category":"job",
    "title":"Line Cook",
    "description":"Full-time seasonal line cook",
    "company_name":"Boardwalk Grill",
    "contact_method":"email",
    "contact_value":"jobs@boardwalk.example",
    "location_city":"Wisconsin Dells",
    "pay_rate":19.25,
    "currency":"USD",
    "shift":"night",
    "is_public":true
  }'
```

Representative response (`201`):
```json
{
  "id": 77,
  "category": "job",
  "title": "Line Cook",
  "description": "Full-time seasonal line cook",
  "company_name": "Boardwalk Grill",
  "contact_method": "email",
  "contact_value": "jobs@boardwalk.example",
  "location_city": "Wisconsin Dells",
  "pay_rate": 19.25,
  "currency": "USD",
  "shift": "night",
  "is_public": true,
  "is_active": true,
  "expires_at": null,
  "created_by": 8,
  "created_at": "2026-01-14T22:05:09.100000"
}
```

---

### 3) `/verify`

#### Upload visa document (multipart, requires token)
```bash
curl -s -X POST "$BASE_URL/verify/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "document=@./sample_visa.pdf" \
  -F "waiver=true"
```

Representative response (`201`):
```json
{
  "id": 91,
  "status": "pending"
}
```

#### Check verification status
```bash
curl -s "$BASE_URL/verify/status" \
  -H "Authorization: Bearer $TOKEN"
```

Representative response (`200`):
```json
{
  "verification_status": "pending",
  "latest_document": {
    "id": 91,
    "user_id": 12,
    "filename": "sample_visa.pdf",
    "status": "pending"
  }
}
```

---

### 4) `/billing`

#### Create Stripe checkout session (requires employer/admin token)
```bash
curl -s -X POST "$BASE_URL/billing/create-checkout-session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purchase_type":"listing",
    "quantity":2,
    "success_url":"http://localhost:3000/billing/success",
    "cancel_url":"http://localhost:3000/billing/cancel"
  }'
```

Representative response (`200`):
```json
{
  "sessionId": "cs_test_a1b2c3",
  "url": "https://checkout.stripe.com/c/pay/cs_test_a1b2c3"
}
```

#### Stripe webhook endpoint
Stripe sends events to:
```text
POST /billing/webhook
```
The endpoint validates `Stripe-Signature` when `STRIPE_WEBHOOK_SECRET` is configured.

Representative response (`200`):
```json
{
  "status": "success"
}
```

---

## Stripe setup requirements

1. **Create products/prices in Stripe**
   - One one-time price for listing credits (`PRICE_LISTING`),
   - One recurring monthly price (`PRICE_MONTHLY`).
2. **Set backend env vars**
   - `STRIPE_SECRET_KEY`, `PRICE_LISTING`, `PRICE_MONTHLY`, `BILLING_SUCCESS_URL`, `BILLING_CANCEL_URL`.
3. **Configure webhook destination**
   - URL: `https://<your-domain>/billing/webhook`
   - Signing secret copied into `STRIPE_WEBHOOK_SECRET`.
4. **Subscribe webhook to expected events**
   - `checkout.session.completed`
   - `invoice.paid`

### Expected webhook behavior
- `checkout.session.completed` with `billing_type=listing`: adds listing credits.
- `checkout.session.completed` with `billing_type=subscription`: fetches Stripe subscription and extends active period.
- `invoice.paid`: refreshes active subscription period from Stripe.

---

## Troubleshooting

### Migration issues

#### `Target database is not up to date`
Run:
```bash
flask db upgrade
```
Then re-run migration generation.

#### Multiple Alembic heads
Symptoms:
```bash
flask db heads
# outputs more than one revision
```
Fix by creating a merge revision:
```bash
flask db merge -m "merge heads" <head_1> <head_2>
flask db upgrade
```

#### Wrong migration order / missing revision
- Confirm `FLASK_APP=app:create_app`.
- Check migration graph:
  ```bash
  flask db history
  flask db current
  ```
- If local dev DB is disposable, recreate DB and rerun `flask db upgrade`.

### Billing/webhook issues
- `Invalid webhook signature`: verify `STRIPE_WEBHOOK_SECRET` and ensure raw body reaches Flask unchanged.
- `Stripe secret key is not configured`: set `STRIPE_SECRET_KEY` in runtime environment.
- Checkout session errors for price config: verify `PRICE_LISTING` / `PRICE_MONTHLY` are valid Stripe **Price IDs** (start with `price_`).

### Auth issues
- `422`/invalid token: confirm `Authorization: Bearer <jwt>` format.
- Login failing: ensure same normalized email and correct password.

---

## Health check
```bash
curl -s "$BASE_URL/health"
```
Expected:
```json
{"status":"ok"}
```
