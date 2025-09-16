# EmotionAI API

FastAPI backend for EmotionAI: secured REST + WebSocket services for auth, profiles, emotional records, breathing, chat agents, and realtime calendar updates.

## What’s inside
- **Auth (JWT)**: Login, register, refresh, me. Access tokens protect all routes except auth/health.
- **Profiles**: Create/update profile, therapy context, agent personality.
- **Emotional Records**: CRUD + range queries on JSONB data.
- **Breathing**: Sessions and patterns.
- **Agents/Chat**: Agent list, status, memory management, chat.
- **Usage**: Per-user limitations.
- **Health**: Liveness endpoints.
- **Realtime (WebSocket)**: Calendar WS updated for all user saved data secured via JWT (query param `token`).

See endpoint-by-endpoint docs with curl examples in:
```text
src/presentation/api/routers/README.md
```

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open interactive docs: `http://localhost:8000/docs`

## Configuration
- **JWT**: Access/refresh with issuer `emotionai-api`. Backend validates `typ=access` and (optionally) `iss`.
- **DB**: PostgreSQL via SQLAlchemy + Alembic migrations.
- **CORS**: Configure in `main.py` as needed.

Environment (example):
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/emotionai
JWT_SECRET=change-me
JWT_ALG=HS256
OPENAI_API_KEY=...
```

## Nginx (TLS AWS Let's Encrypt HTTP-01 + reverse proxy)
Production proxy in with AWS Let's Encrypt HTTP-01 terminates TLS and forwards to Uvicorn. See:
```text
deploy/nginx/emotionai.conf
```

Ensure Authorization header is forwarded:
```nginx
proxy_set_header Authorization $http_authorization;
```

## Mobile Logs (optional)
- Enable via env: `MOBILE_LOGS_ENABLED=true`, region/group configurable (`MOBILE_LOGS_REGION`, `MOBILE_LOGS_GROUP`).
- App will POST batches to `/v1/api/mobile-logs` when run with `--dart-define=MOBILE_LOGS=true`.
- CloudWatch role requires: logs:CreateLogGroup, CreateLogStream, DescribeLogStreams, PutLogEvents.

## Project layout
```text
src/
  presentation/api/routers/   # FastAPI routers (secured by JWT)
  infrastructure/             # DB, external services, repositories
  domain/                     # Entities, value objects, interfaces
  application/                # Use-cases, services, dtos
main.py                       # App setup (redirect_slashes disabled, global auth deps)
```

## Testing
```bash
pytest -q
```

## Deploy
- Uvicorn/Gunicorn behind Nginx (see deploy/nginx)
- Environment variables for secrets (no hardcoding)

## Notes
- All routes under `/v1/api/*` require Authorization: Bearer <access_token>, except `/v1/api/auth/*` and `/health*`.
- WebSocket connects to `/v1/api/calendar/ws?token=<access_token>` and validates `typ=access`.
