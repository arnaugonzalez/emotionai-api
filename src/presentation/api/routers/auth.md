# Auth

Base: `/v1/api/auth` (public)

Set helper variables:
```bash
BASE_URL=${BASE_URL}
JSON='Content-Type: application/json'
```

Register
```bash
curl -sS -X POST "$BASE_URL/v1/api/auth/register" \
  -H "$JSON" \
  -d '{"email":"test@example.com","password":"Passw0rd!"}'
```

Login
```bash
curl -sS -X POST "$BASE_URL/v1/api/auth/login" \
  -H "$JSON" \
  -d '{"email":"test@example.com","password":"Passw0rd!"}'
```

Refresh
```bash
curl -sS -X POST "$BASE_URL/v1/api/auth/refresh" \
  -H "$JSON" \
  -H "Authorization: Bearer $REFRESH"
```

Me (requires access token)
```bash
curl -sS "$BASE_URL/v1/api/auth/me" -H "Authorization: Bearer $ACCESS"
```


