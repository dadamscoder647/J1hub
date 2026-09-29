# J1Hub Frontend

React + Vite client for the versioned J1Hub API.

## Local setup

```bash
cp .env.example .env.local
npm ci
npm run dev
```

The default API base is `http://localhost:5000/api/v1`. Set `VITE_API_BASE_URL` to the full API base, including `/api/v1`, when using another backend. Configure backend `ORIGINS` to include `http://localhost:5173` for local development.

## Role journeys

- Workers register, upload verification documents, search listings, apply after approval, and follow application status.
- Employers see current listing credits and subscription status, start Stripe Checkout, publish listings, review applications, and update their status.
- Administrators review the paginated verification queue, download files, and approve or reject submissions.

Administrator accounts are provisioned through a trusted backend process. The public registration screen offers worker and employer accounts only.

## Checks

```bash
npm run build
npm run test:e2e
```

Playwright smoke tests mock API responses and exercise the three role dashboards. They do not validate a deployed API, storage provider, or live Stripe configuration.
