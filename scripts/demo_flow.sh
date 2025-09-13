#!/usr/bin/env bash
set -euo pipefail

# =============================
# Configuration
# =============================
BASE="http://127.0.0.1:8000"   # Local Uvicorn
# BASE="https://emotionai.duckdns.org"  # Production behind Nginx/Let's Encrypt

EMAIL="test@demo.com"
PASSWORD="test123"
FIRST="test"
LAST="demo"

have_jq() { command -v jq >/dev/null 2>&1; }
pp_json() { if have_jq; then jq .; else cat; fi; }

auth_header() {
  echo "Authorization: Bearer $1"
}

# =============================
# Auth: register/login/me/refresh
# =============================
echo "== AUTH: register =="
REGISTER_RESP=$(curl -sS -X POST "$BASE/v1/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'","first_name":"'"$FIRST"'","last_name":"'"$LAST"'"}')
echo "$REGISTER_RESP" | pp_json

if have_jq; then
  ACCESS=$(echo "$REGISTER_RESP" | jq -r '.access_token')
  REFRESH=$(echo "$REGISTER_RESP" | jq -r '.refresh_token')
else
  ACCESS=$(echo "$REGISTER_RESP" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
  REFRESH=$(echo "$REGISTER_RESP" | sed -n 's/.*"refresh_token":"\([^"]*\)".*/\1/p')
fi
echo "ACCESS: ${ACCESS:0:16}..."

echo "== AUTH: me =="
curl -sS "$BASE/v1/api/auth/me" -H "$(auth_header "$ACCESS")" | pp_json

echo "== AUTH: refresh (endpoint test only) =="
if [[ -n "${REFRESH:-}" ]]; then
  curl -sS -X POST "$BASE/v1/api/auth/refresh" \
    -H "Content-Type: application/json" \
    -d '{"refresh_token":"'"$REFRESH"'"}' | pp_json
else
  echo "(refresh_token not available)"
fi

# =============================
# Profile
# =============================
echo "== PROFILE: create/update =="
curl -sS -X POST "$BASE/v1/api/profile" \
  -H "Content-Type: application/json" \
  -H "$(auth_header "$ACCESS")" \
  -d '{
        "first_name":"'"$FIRST"'",
        "last_name":"'"$LAST"'",
        "user_profile_data":{"personality":"INTJ"}
      }' | pp_json

echo "== PROFILE: get =="
curl -sS "$BASE/v1/api/profile" -H "$(auth_header "$ACCESS")" | pp_json

echo "== PROFILE: status =="
curl -sS "$BASE/v1/api/profile/status" -H "$(auth_header "$ACCESS")" | pp_json

echo "== PROFILE: therapy-context PUT/GET/DELETE =="
curl -sS -X PUT "$BASE/v1/api/profile/therapy-context" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"therapy_context":{"topic":"sleep"}}' | pp_json
curl -sS "$BASE/v1/api/profile/therapy-context" -H "$(auth_header "$ACCESS")" | pp_json
curl -sS -X DELETE "$BASE/v1/api/profile/therapy-context" -H "$(auth_header "$ACCESS")" | pp_json

# =============================
# Data: custom emotions
# =============================
echo "== DATA: create custom emotion =="
curl -sS -X POST "$BASE/v1/api/custom_emotions/" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"name":"gratitude","color":16776960}' | pp_json

echo "== DATA: list custom emotions =="
curl -sS "$BASE/v1/api/custom_emotions/" -H "$(auth_header "$ACCESS")" | pp_json

# =============================
# Records: emotional records
# =============================
echo "== RECORDS: create standard =="
curl -sS -X POST "$BASE/v1/api/emotional_records/" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"emotion":"happy","intensity":7,"description":"Feeling good via demo"}' | pp_json

echo "== RECORDS: create from custom emotion =="
curl -sS -X POST "$BASE/v1/api/emotional_records/from_custom_emotion" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"custom_emotion_name":"gratitude","custom_emotion_color":16776960,"intensity":6,"description":"Grateful"}' | pp_json

echo "== RECORDS: list =="
curl -sS "$BASE/v1/api/emotional_records/" -H "$(auth_header "$ACCESS")" | pp_json

# =============================
# Breathing: sessions & patterns
# =============================
echo "== BREATHING: create session =="
curl -sS -X POST "$BASE/v1/api/breathing_sessions/" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"pattern":"Box Breathing","rating":4,"comment":"Nice"}' | pp_json

echo "== BREATHING: list sessions =="
curl -sS "$BASE/v1/api/breathing_sessions/" -H "$(auth_header "$ACCESS")" | pp_json

echo "== BREATHING: create pattern =="
curl -sS -X POST "$BASE/v1/api/breathing_patterns/" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"name":"Custom 4-4-6","inhale_seconds":4,"hold_seconds":0,"exhale_seconds":6,"cycles":5,"rest_seconds":0}' | pp_json

echo "== BREATHING: list patterns =="
curl -sS "$BASE/v1/api/breathing_patterns/" -H "$(auth_header "$ACCESS")" | pp_json

# =============================
# Usage
# =============================
echo "== USAGE: user limitations =="
curl -sS "$BASE/v1/api/user/limitations" -H "$(auth_header "$ACCESS")" | pp_json

# =============================
# Chat (may require API keys for LLM)
# =============================
echo "== CHAT: agents list =="
curl -sS "$BASE/v1/api/agents" | pp_json

echo "== CHAT: status (therapy) =="
curl -sS "$BASE/v1/api/agents/therapy/status" -H "$(auth_header "$ACCESS")" | pp_json || true

echo "== CHAT: send message =="
curl -sS -X POST "$BASE/v1/api/chat" \
  -H "Content-Type: application/json" -H "$(auth_header "$ACCESS")" \
  -d '{"agent_type":"therapy","message":"Hello, I\'m feeling good."}' | pp_json || true

echo "== CHAT: clear memory (therapy) =="
curl -sS -X DELETE "$BASE/v1/api/agents/therapy/memory" -H "$(auth_header "$ACCESS")" | pp_json || true

# =============================
# Dev seed (development environment only)
# =============================
echo "== DEV SEED: load preset data (dev only) =="
curl -sS -X POST "$BASE/v1/api/dev/seed/load_preset_data" -H "$(auth_header "$ACCESS")" | pp_json || true

echo "== DEV SEED: reset (dev only) =="
curl -sS -X POST "$BASE/v1/api/dev/seed/reset" -H "$(auth_header "$ACCESS")" | pp_json || true

echo "\nDemo flow completed."