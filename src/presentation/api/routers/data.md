# Custom Emotions

Base: `/v1/api/custom_emotions` (JWT required)

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
JSON='Content-Type: application/json'
```

List
```bash
curl -sS "$BASE_URL/v1/api/custom_emotions/" -H "$AUTH"
```

Create
```bash
curl -sS -X POST "$BASE_URL/v1/api/custom_emotions/" \
  -H "$AUTH" -H "$JSON" \
  -d '{"name":"pride","color":"#FFAA00"}'
```


