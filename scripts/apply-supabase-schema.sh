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

python3 - <<'PY'
from pathlib import Path
import json
import os
import subprocess
import tempfile

root = Path.cwd()
migration_files = sorted((root / 'supabase' / 'migrations').glob('*.sql'))
if not migration_files:
    raise SystemExit('No migration files found in supabase/migrations.')

sql = '\n\n'.join(path.read_text() for path in migration_files)
payload_file = Path(tempfile.gettempdir()) / 'supabase_migration_apply_payload.json'
payload_file.write_text(json.dumps({'query': sql}))

url = f"https://api.supabase.com/v1/projects/{os.environ['SUPABASE_PROJECT_REF']}/database/query"
cmd = [
    'curl', '-sS', '--fail-with-body', url,
    '-H', f"Authorization: Bearer {os.environ['SUPABASE_ACCESS_TOKEN']}",
    '-H', 'Content-Type: application/json',
    '-H', 'Accept: application/json',
    '-H', 'User-Agent: ielts-writing-schema-apply/1.0',
    '--data-binary', f'@{payload_file}',
]
result = subprocess.run(cmd, text=True, capture_output=True)
if result.returncode != 0:
    print(result.stdout)
    print(result.stderr)
    raise SystemExit(result.returncode)

print(result.stdout)
PY
