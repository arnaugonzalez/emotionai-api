# Profile

Base: `/v1/api/profile` (JWT required). Trailing and non-trailing slashes accepted on root.

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
JSON='Content-Type: application/json'
```

Get Profile
```bash
curl -sS "$BASE_URL/v1/api/profile" -H "$AUTH"
```

Create/Update Profile
```bash
curl -sS -X POST "$BASE_URL/v1/api/profile" \
  -H "$AUTH" -H "$JSON" \
  -d '{"name":"Alex","age":30,"goals":["sleep","stress"]}'
```

Get Profile Status
```bash
curl -sS "$BASE_URL/v1/api/profile/status" -H "$AUTH"
```

Update Therapy Context
```bash
curl -sS -X PUT "$BASE_URL/v1/api/profile/therapy-context" \
  -H "$AUTH" -H "$JSON" \
  -d '{"context":"Recently feeling more anxious before meetings"}'
```

Set Agent Personality
```bash
curl -sS -X PUT "$BASE_URL/v1/api/profile/agent-personality" \
  -H "$AUTH" -H "$JSON" \
  -d '{"personality":"empathetic_supportive"}'
```


