# Realtime (WebSocket)

Endpoint: `/v1/api/calendar/ws` (JWT required as query `token`)

Helpers:
```bash
BASE_URL=${BASE_URL}
ACCESS=${ACCESS:?set access token}
WS=${BASE_URL/https/wss}
```

Connect (wscat)
```bash
wscat -c "$WS/v1/api/calendar/ws?token=$ACCESS"
```

Invalid token results in close code 1008 (policy violation).


