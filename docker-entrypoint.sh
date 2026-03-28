#!/bin/sh
# Read Docker secrets into environment variables
if [ -f /run/secrets/postgres_password ]; then
    PG_PASS=$(cat /run/secrets/postgres_password)
    export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-postgres}:${PG_PASS}@postgres:5432/emotionai_db"
fi
if [ -f /run/secrets/redis_password ]; then
    REDIS_PASS=$(cat /run/secrets/redis_password)
    export REDIS_URL="redis://:${REDIS_PASS}@redis:6379/0"
fi
if [ -f /run/secrets/emotionai_secret_key ]; then
    export SECRET_KEY=$(cat /run/secrets/emotionai_secret_key)
fi
exec "$@"
