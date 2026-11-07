#!/usr/bin/env bash
# Deploy furniture_cad jobs worker to Fly.io. See docs/deploy-worker.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${FLY_APP:-image-to-cad-worker}"
CONFIG="$ROOT/lab/furniture_cad/fly.toml"
DOCKERFILE="$ROOT/lab/furniture_cad/Dockerfile"

if ! command -v fly >/dev/null 2>&1 && ! command -v flyctl >/dev/null 2>&1; then
  echo "Fly CLI not found. Install: curl -L https://fly.io/install.sh | sh" >&2
  exit 1
fi
FLY="$(command -v fly || command -v flyctl)"

if ! "$FLY" auth whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: fly auth login" >&2
  exit 1
fi

if ! "$FLY" apps list 2>/dev/null | grep -q "$APP"; then
  echo "Creating app $APP…"
  "$FLY" apps create "$APP" || true
fi

echo "Deploying $APP…"
"$FLY" deploy --config "$CONFIG" --dockerfile "$DOCKERFILE" --ha=false -a "$APP"
echo
echo "Health:"
"$FLY" status -a "$APP" || true
HOST="$("$FLY" info -a "$APP" --json 2>/dev/null | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const j=JSON.parse(d);console.log((j.Hostname||j.hostname||''))}catch(e){}})" || true)"
if [[ -n "${HOST:-}" ]]; then
  echo "Set Vercel WORKER_JOBS_URL=https://$HOST"
  echo "Set Vercel WORKER_JOBS_TOKEN to the same secret as Fly."
fi
echo "Done. Full steps: docs/deploy-worker.md"
