# API Routers Index

Base path: `/v1/api`

- `auth` – Public endpoints for login/register/refresh/me
- `profile` – Profile CRUD, status, therapy context, agent personality
- `records` – Emotional records CRUD and queries
- `breathing` – Breathing sessions and patterns
- `data` – Custom emotions
- `usage` – User limitations/usage
- `chat` – Agents list/status/memory and chat
- `ws` – Realtime calendar WebSocket (JWT in query)
- `health` – Health endpoints (root-level `/health/`)
- `dev_seed` – Development-only seed/reset

Detailed docs with curl examples:
```text
auth.md
profile.md
records.md
breathing.md
data.md
usage.md
chat.md
ws.md
health.md
dev_seed.md
```


