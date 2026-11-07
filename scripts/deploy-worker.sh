#!/usr/bin/env bash
# Deploy furniture_cad jobs worker to Fly.io. See docs/deploy-worker.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${FLY_APP:-image-to-cad-worker}"
LAB="$ROOT/lab/furniture_cad"

if ! command -v fly >/dev/null 2>&1 && ! command -v flyctl >/dev/null 2>&1; then
  echo "Fly CLI not found. Install: curl -L https://fly.io/install.sh | sh" >&2
  exit 1
fi
FLY="$(command -v fly || command -v flyctl)"

if ! "$FLY" auth whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: fly auth login" >&2
  exit 1
fi

if ! "$FLY" status -a "${APP}" >/dev/null 2>&1; then
  echo "Creating app ${APP}..."
  "$FLY" apps create "${APP}" --yes
fi

echo "Deploying ${APP} (build context: lab/furniture_cad)..."
# IMPORTANT: run from lab/furniture_cad so Dockerfile COPY paths resolve.
cd "${LAB}"
"$FLY" deploy \
  --app "${APP}" \
  --config fly.toml \
  --dockerfile Dockerfile \
  --ha=false

echo
echo "Health:"
"$FLY" status -a "${APP}" || true
HOST="${APP}.fly.dev"
echo
echo "Next:"
echo "  On Vercel set WORKER_JOBS_URL=https://${HOST}"
echo "  and WORKER_JOBS_TOKEN (same as Fly secret), then redeploy"
echo "Done. Full steps: docs/deploy-worker.md"
