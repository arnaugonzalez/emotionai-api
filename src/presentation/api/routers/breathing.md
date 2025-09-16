# Breathing

Base: `/v1/api`

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
JSON='Content-Type: application/json'
```

List Breathing Sessions
```bash
curl -sS "$BASE_URL/v1/api/breathing_sessions/" -H "$AUTH"
```

Create Breathing Session
```bash
curl -sS -X POST "$BASE_URL/v1/api/breathing_sessions/" \
  -H "$AUTH" -H "$JSON" \
  -d '{"pattern":"box","duration_seconds":300,"completed":true}'
```

List Breathing Patterns
```bash
curl -sS "$BASE_URL/v1/api/breathing_patterns/" -H "$AUTH"
```


