# Deploy the shop-grade jobs worker (Fly.io)

Vercel serves the app and relays `/api/jobs` → a **long-running worker** that runs build123d + the Messages tool loop. Without a reachable worker, Shop-grade Create falls back to Classic (Vercel `/api/messages` proxy).

## Architecture

```
Browser  →  Vercel /api/jobs  →  Fly worker :8787
                │                    │
         WORKER_JOBS_URL      ANTHROPIC_API_KEY
         WORKER_JOBS_TOKEN    WORKER_JOBS_TOKEN (same secret)
```

Leave **Advanced → Worker URL empty** in production so the browser never sees the worker token. Local Docker can still use Worker URL `http://127.0.0.1:8787` (no token, or matching token).

## 1. Install Fly CLI and log in

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

## 2. Create the app + secrets

From the repo root:

```bash
fly apps create image-to-cad-worker --yes   # once; rename in fly.toml if taken

# Secrets must be KEY=VALUE (not KEY VALUE) — this is the "0 and 1 arg" error if wrong:
TOKEN="$(openssl rand -hex 24)"
fly secrets set -a image-to-cad-worker \
  "ANTHROPIC_API_KEY=sk-ant-..." \
  "WORKER_JOBS_TOKEN=${TOKEN}"
echo "Save this token for Vercel: ${TOKEN}"
```

Save the token — you need the **same** value on Vercel as `WORKER_JOBS_TOKEN`.

## 3. Deploy

```bash
./scripts/deploy-worker.sh
# or (must run from lab/furniture_cad so COPY paths work):
cd lab/furniture_cad
fly deploy -a image-to-cad-worker --ha=false
```

Health: `https://image-to-cad-worker.fly.dev/health` → `{"ok":true,...}`.

Optional disk (survive machine stops):

```bash
fly volumes create jobs_data --app image-to-cad-worker --region sjc --size 10
# then uncomment [mounts] in lab/furniture_cad/fly.toml and redeploy
```

## 4. Point Vercel at the worker

In the Vercel project → Settings → Environment Variables:

| Name | Value |
| --- | --- |
| `WORKER_JOBS_URL` | `https://image-to-cad-worker.fly.dev` |
| `WORKER_JOBS_TOKEN` | same secret as Fly |

Redeploy the Vercel app. Shop-grade Create should show **Worker online** on the Check tab (via `GET /api/jobs`).

## 5. Local Docker (optional)

```bash
docker build -t furniture-cad-worker -f lab/furniture_cad/Dockerfile lab/furniture_cad
docker run --rm -p 8787:8787 \
  -e ANTHROPIC_API_KEY \
  -e WORKER_JOBS_TOKEN=dev \
  furniture-cad-worker
```

## Cost / sizing

- Machine: `shared-cpu-2x` / **4 GB** (build123d); auto-stops when idle (`min_machines_running = 0`).
- Cold start after idle can take ~30–60 s; the UI polls until ready.
- Spend caps remain `$2/run` · `$25/day` on the worker.

### Fly trial limit (important)

On a **Fly trial without a payment method**, machines are **force-stopped after 5 minutes**. Shop-grade builds often need longer, so the job looks “stuck” and job files in `/tmp` are wiped on restart.

**Fix:** add a credit card at [fly.io/trial](https://fly.io/trial) (or upgrade), then redeploy. Optional: uncomment the `[mounts]` volume in `fly.toml` so job artifacts survive restarts.

## Smoke test

```bash
curl -s https://image-to-cad-worker.fly.dev/health
curl -s -H "Authorization: Bearer $WORKER_JOBS_TOKEN" \
  https://image-to-cad-worker.fly.dev/jobs
# After Vercel env is set:
curl -s https://YOUR_VERCEL_HOST/api/jobs
```
