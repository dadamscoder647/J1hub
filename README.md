# J1hub

The j1 app that will be popular in the dells.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your application environment (database URL, JWT secrets, etc.) in a `.env` file as needed.

## Seed script credentials

The seed scripts read admin/employer/worker credentials from environment variables.

### Supported variables

- `SEED_ADMIN_EMAIL`
- `SEED_ADMIN_PASSWORD`
- `SEED_EMPLOYER_EMAIL`
- `SEED_EMPLOYER_PASSWORD`
- `SEED_WORKER_EMAIL`
- `SEED_WORKER_PASSWORD`

### Local-development defaults

If any seed variable is not set, scripts print a warning and use local-development defaults:

- Admin: `admin@example.com` / `AdminPass123`
- Employer: `employer@example.com` / `EmployerPass123`
- Worker: `worker@example.com` / `WorkerPass123`

> Password fallback warnings are redacted in logs.
>
> Do not use these defaults in shared, staging, or production environments.

### Example usage

```bash
export SEED_ADMIN_EMAIL="admin+local@example.com"
export SEED_ADMIN_PASSWORD="change-me"
export SEED_EMPLOYER_EMAIL="employer+local@example.com"
export SEED_EMPLOYER_PASSWORD="change-me"
export SEED_WORKER_EMAIL="worker+local@example.com"
export SEED_WORKER_PASSWORD="change-me"

python scripts/seed_admin.py
python scripts/seed_demo_data.py
python scripts/bootstrap_demo.py
```
