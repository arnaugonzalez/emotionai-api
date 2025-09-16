# Chat & Agents

Base: `/v1/api`

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
JSON='Content-Type: application/json'
```

List Agents
```bash
curl -sS "$BASE_URL/v1/api/agents" -H "$AUTH"
```

Agent Status
```bash
curl -sS "$BASE_URL/v1/api/agents/therapy/status" -H "$AUTH"
```

Clear Agent Memory
```bash
curl -sS -X DELETE "$BASE_URL/v1/api/agents/therapy/memory" -H "$AUTH"
```

Send Chat Message
```bash
curl -sS -X POST "$BASE_URL/v1/api/chat" \
  -H "$AUTH" -H "$JSON" \
  -d '{"agent_type":"therapy","message":"Hello, I am feeling good."}'
```


