# J1hub Verification and Listings CURL Examples

Set environment variables for convenience:

```bash
export BASE_URL="http://localhost:5000"
export ADMIN_TOKEN="<admin access token>"
export EMPLOYER_TOKEN="<employer access token>"
export WORKER_TOKEN="<worker access token>"
```

## Upload Visa Document

```bash
curl -X POST "$BASE_URL/verify/upload" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -F "doc_type=passport" \
  -F "file=@/path/to/passport.pdf"
```

## Check Verification Status

```bash
curl -X GET "$BASE_URL/verify/status" \
  -H "Authorization: Bearer $WORKER_TOKEN"
```

## Admin Review Pending Documents

```bash
curl -X GET "$BASE_URL/admin/verify/pending" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Admin Approve Document

```bash
curl -X POST "$BASE_URL/admin/verify/1/approve" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Looks good"}'
```

## Admin Deny Document

```bash
curl -X POST "$BASE_URL/admin/verify/1/deny" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Please upload a clearer copy"}'
```

## Search Listings

```bash
curl -X GET "$BASE_URL/listings?category=job&q=server&city=miami"
```

## Create Listing (Employer/Admin)

```bash
curl -X POST "$BASE_URL/listings" \
  -H "Authorization: Bearer $EMPLOYER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "job",
    "title": "Seasonal Server",
    "description": "Serve guests at resort events.",
    "company_name": "Sunshine Resort",
    "contact_method": "email",
    "contact_value": "hr@sunshine.example",
    "location_city": "Miami",
    "pay_rate": 18.5,
    "currency": "USD",
    "shift": "Evenings"
  }'
```

## Apply to Listing (Worker)

```bash
curl -X POST "$BASE_URL/listings/1/apply" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I have three seasons of experience."}'
```
