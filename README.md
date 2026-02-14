# J1hub
The j1 app that will be popular in the dells.

## API contract
- OpenAPI source of truth: `openapi.yaml`.
- Canonical endpoint prefix: `/api/v1`.
- Legacy unversioned endpoints are temporary aliases controlled by `API_ENABLE_LEGACY_ROUTES=true|false`.
- CI enforces that changes to `app.py` or `routes/*.py` must include an OpenAPI spec update.
