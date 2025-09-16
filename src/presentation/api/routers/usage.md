# Usage

Base: `/v1/api/user/limitations` (JWT required)

Helpers:
```bash
BASE_URL=${BASE_URL}
AUTH="Authorization: Bearer $ACCESS"
```

Get User Limitations
```bash
curl -sS "$BASE_URL/v1/api/user/limitations" -H "$AUTH"
```


