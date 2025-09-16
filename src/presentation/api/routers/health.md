# Health

Endpoints are public and mounted at the root (no `/v1/api` prefix):

```bash
BASE_URL=${BASE_URL}
curl -sS "$BASE_URL/health" | jq .
curl -sS "$BASE_URL/health/detailed" | jq .
```


