# J1hub

Backend API for authentication, visa verification workflows, listings, and billing support.

## Verification API (OpenAPI-style endpoint table)

All endpoints require `Authorization: Bearer <JWT>`.

| Method | Path | Role | Request payload | Response |
|---|---|---|---|---|
| `POST` | `/verify/upload` | Worker | `multipart/form-data` with `document=<file>` and `waiver=<bool>` | `201` with `{ "id": <int>, "status": "pending" }` |
| `GET` | `/verify/status` | Worker | None | `200` with `{ "verification_status": "pending\|approved\|rejected", "latest_document": {...}\|null }` |
| `GET` | `/verify/doc/{id}` | Admin | None | `200` file download |
| `GET` | `/admin/verify/pending` | Admin | None | `200` list of pending documents |
| `POST` | `/admin/verify/{id}/approve` | Admin | None | `200` with approved document/user status |
| `POST` | `/admin/verify/{id}/reject` | Admin | Optional JSON body `{ "review_note": "..." }` | `200` with rejected document/user status |

### Deprecated legacy aliases

These aliases are still enabled temporarily for backward compatibility and return a deprecation `Warning` response header:

- `GET /verify/pending`
- `POST /verify/{id}/approve`
- `POST /verify/{id}/reject`

Use the `/admin/verify/*` namespace for all admin verification actions.
