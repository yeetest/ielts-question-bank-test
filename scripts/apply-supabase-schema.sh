#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "Missing SUPABASE_ACCESS_TOKEN."
  exit 1
fi

if [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
  echo "Missing SUPABASE_DB_PASSWORD."
  exit 1
fi

if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
  if [[ -n "${SUPABASE_URL:-}" ]]; then
    SUPABASE_PROJECT_REF="${SUPABASE_URL#https://}"
    SUPABASE_PROJECT_REF="${SUPABASE_PROJECT_REF%%.*}"
  else
    echo "Missing SUPABASE_PROJECT_REF."
    exit 1
  fi
fi

export SUPABASE_ACCESS_TOKEN

npx supabase@latest link --project-ref "$SUPABASE_PROJECT_REF" --password "$SUPABASE_DB_PASSWORD"
npx supabase@latest db push
