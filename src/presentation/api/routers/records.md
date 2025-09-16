# Emotional Records

Base: `/v1/api/emotional_records` (JWT required)

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
JSON='Content-Type: application/json'
```

List Records
```bash
curl -sS "$BASE_URL/v1/api/emotional_records/" -H "$AUTH"
```

Create Record
```bash
curl -sS -X POST "$BASE_URL/v1/api/emotional_records/" \
  -H "$AUTH" -H "$JSON" \
  -d '{"emotion":"joy","intensity":7,"description":"Walked in the sun","context_data":{"custom_emotion_name":"joy"}}'
```

Get Records By Date Range
```bash
curl -sS "$BASE_URL/v1/api/emotional_records?start=2024-01-01&end=2024-12-31" -H "$AUTH"
```


