# Frontend Billing Integration

Use these endpoints to show employer/admin billing state in account settings and listing posting flows.

## Auth + Roles

All billing visibility endpoints require a valid JWT and are limited to `employer` and `admin` roles.

- Unauthorized role response: `403`
- Missing token response: `401`

## Billing Status

`GET /billing/status`

Returns a lightweight account snapshot:

```json
{
  "listing_credits": 3,
  "has_active_subscription": true,
  "active_until": "2026-03-01T00:00:00"
}
```

Frontend usage suggestions:

- Gate listing publishing UX if `listing_credits === 0 && !has_active_subscription`.
- Display `active_until` in local timezone when present.

## Billing History

`GET /billing/history?limit=25`

Returns webhook-logged events for the current employer/admin account.

```json
{
  "count": 2,
  "events": [
    {
      "id": 9,
      "provider": "stripe",
      "event_type": "listing_credits_added",
      "provider_event_id": "evt_123",
      "details": {
        "quantity": 5
      },
      "created_at": "2026-02-14T12:30:00"
    }
  ]
}
```

- `limit` is optional and clamped between `1` and `100`.
- Use history for simple activity timeline cards rather than full invoice rendering.
