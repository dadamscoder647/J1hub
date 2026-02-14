# J1Hub Frontend

React + Vite frontend for auth and role-based dashboards.

## Local setup

1. Copy env vars:
   ```bash
   cp .env.example .env.local
   ```
2. Install and run:
   ```bash
   npm install
   npm run dev
   ```

By default, API requests use `VITE_API_BASE_URL=http://localhost:5000` which matches the Flask backend. This is CORS-safe with backend `CORS_ORIGINS` configured to include the frontend origin (for local dev: `http://localhost:5173`).

## Features

- Auth screens: register/login (`/auth/register`, `/auth/login`)
- JWT access-token storage with Axios request/response interceptors
- 401 retry strategy via optional refresh endpoint fallback
- Role-aware routing:
  - Worker dashboard: verification upload/status, listing search, apply
  - Employer dashboard: checkout purchase, listing create flow
  - Admin dashboard: pending queue and approve/reject actions
- UX states: loading/error/empty handling

## E2E smoke tests

```bash
npm run test:e2e
```

Covers:
- worker register → verify/status → apply flow
- employer purchase → listing create flow
- admin pending queue → approve flow
