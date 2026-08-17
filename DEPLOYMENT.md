# Deployment Guide 🚀

How to deploy the AI Personal Assistant (Telegram bot agent) to production.

---

## 🎯 The Expert Path — How I Would Deploy This

If I were deploying this exact project today, this is precisely what I'd do, in order, with the reasoning. Total time: ~30–45 minutes.

### Decision 1: Where to host

| Choice       | My pick for this project                                          | Why                                                                                                                                                                                           |
| ------------ | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Provider** | Hetzner CX22 (€4/mo, 2 vCPU/4GB) or DigitalOcean ($12/mo droplet) | The stack (FastAPI + Postgres + Redis + Qdrant + Celery ×2 + nginx) is memory-hungry; 2GB is the floor, 4GB is comfortable. PaaS (Railway/Render) gets awkward with 7 cooperating containers. |
| **Mode**     | Webhook (not polling)                                             | Webhooks give instant response, no wasted long-poll cycles, and survive multi-worker deployments. Polling breaks the moment you run 2 replicas (getUpdates conflicts).                        |
| **TLS**      | Caddy in front **or** nginx + certbot                             | Telegram rejects non-HTTPS webhooks. Caddy = zero-config renewal; nginx is already in this repo's compose.                                                                                    |
| **Secrets**  | `.env` on server, chmod 600, never in git                         | Simple and sufficient at this scale. (At team scale: move to SOPS/Vault.)                                                                                                                     |

### Decision 2: One production change before shipping

The single most impactful risk in this codebase: **`alembic/versions/` is empty**, so schema is managed by `create_all` at boot. That's fine for a solo bot, but the first time you change a model column in production, `create_all` won't alter existing tables. So on day one I'd run:

```bash
docker compose exec app alembic revision --autogenerate -m "baseline"
docker compose exec app alembic upgrade head
```

A baseline migration now = painless schema changes later. Five minutes, huge payoff.

### The runbook

```bash
# ── 1. Server prep (Ubuntu 22.04) ─────────────────────────────
ssh root@SERVER_IP
adduser deploy && usermod -aG sudo,docker deploy
ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable
curl -fsSL https://get.docker.com | sh          # installs docker + compose plugin

# ── 2. DNS ────────────────────────────────────────────────────
# Create an A record:  bot.example.com → SERVER_IP
# Verify before continuing (propagation):
dig +short bot.example.com

# ── 3. App setup ──────────────────────────────────────────────
sudo -iu deploy
git clone <your-repo-url> telebot && cd telebot

# ── 4. Production .env (never commit; chmod 600) ─────────────
cat > .env <<'EOF'
APP_DEBUG=false
SECRET_KEY=<python3 -c "import secrets;print(secrets.token_hex(32))">
TELEGRAM_BOT_TOKEN=<from @BotFather>
WEBHOOK_SECRET=<python3 -c "import secrets;print(secrets.token_hex(24))">
WEBHOOK_URL=https://bot.example.com
OPENROUTER_API_KEY=<from openrouter.ai>
POSTGRES_USER=assistant
POSTGRES_PASSWORD=<strong-random>
POSTGRES_DB=assistant_agent
GOOGLE_CLIENT_ID=<...>
GOOGLE_CLIENT_SECRET=<...>
GOOGLE_REDIRECT_URI=https://bot.example.com/api/v1/auth/google/callback
EOF
chmod 600 .env

# ── 5. TLS cert (standalone certbot, before nginx grabs :80) ─
sudo apt install -y certbot
sudo certbot certonly --standalone -d bot.example.com
sudo mkdir -p nginx/certs
sudo cp /etc/letsencrypt/live/bot.example.com/{fullchain,privkey}.pem nginx/certs/
sudo chown deploy:deploy nginx/certs/*.pem

# ── 6. Enable HTTPS in nginx + mount certs ────────────────────
#    nginx/nginx.conf → uncomment the HTTPS server block, set server_name
#    docker-compose.yml → uncomment the certs volume mount

# ── 7. Boot the stack ─────────────────────────────────────────
docker compose up --build -d
docker compose ps                      # all 7 containers Up (healthy)

# ── 8. Verify the contract with Telegram ──────────────────────
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq
# Expect: url="https://bot.example.com/api/v1/telegram/webhook",
#         pending_update_count=0, no last_error_message

curl -s https://bot.example.com/api/v1/health   # {"status":"ok",...}

# ── 9. Baseline migration (do this NOW — see Decision 2) ──────
docker compose exec app alembic revision --autogenerate -m baseline
docker compose exec app alembic upgrade head

# ── 10. Smoke test ────────────────────────────────────────────
# Send /start to the bot in Telegram → it must reply.
# Send /connectcalendar → OAuth link must work (proves GOOGLE_REDIRECT_URI).
# docker compose logs -f app while you do it.
```

### What I'd monitor from day one

1. `getWebhookInfo` → `pending_update_count` climbing = your handler is failing/timeout. Check `docker compose logs app`.
2. Disk space — Postgres + Qdrant volumes grow. `docker system prune -f` monthly; log rotation is already configured in compose.
3. OpenRouter 429s in logs → add rate limiting/backoff in `app/llm/client.py` before users notice slow replies.
4. Cert expiry — `certbot renew` via cron + `docker compose exec nginx nginx -s reload`. (Or swap nginx for Caddy and never think about it.)

### The 3 mistakes I'd make sure to avoid

1. **Running polling and webhook simultaneously** — a leftover `getUpdates` loop after switching to webhooks silently eats updates. `deleteWebhook`/stop pollers when flipping modes.
2. **`APP_DEBUG=true` in prod** — it echoes SQL, widens CORS to `*`, and gates table creation oddly. Grep the `.env` twice.
3. **Testing OAuth last** — Google OAuth is the most env-sensitive part (`GOOGLE_REDIRECT_URI` must match Google Cloud Console exactly, including https and path). I'd test `/connectcalendar` immediately after boot, not after "everything else works."

---

## Choose Your Deployment Mode

|                           | **Polling** (simplest)           | **Webhook** (recommended for production) |
| ------------------------- | -------------------------------- | ---------------------------------------- |
| Public IP / domain needed | ❌ No                            | ✅ Yes                                   |
| HTTPS needed              | ❌ No                            | ✅ Yes                                   |
| Receives updates          | Bot asks Telegram (`getUpdates`) | Telegram pushes to your server           |
| Latency                   | Slightly higher                  | Lowest                                   |
| Best for                  | Dev, testing, home machines      | 24/7 production servers                  |

---

## Option A — Deploy with Docker Compose (Recommended)

### Prerequisites

- A Linux server (Ubuntu 22.04+, 2 GB RAM minimum) with:
  - Docker + Docker Compose plugin: `curl -fsSL https://get.docker.com | sh`
  - Ports **80** and **443** open in the firewall/cloud security group
- A domain name pointed at the server (e.g. `bot.example.com`) — **required for webhooks**, since Telegram only delivers webhooks over HTTPS
- Your bot token from [@BotFather](https://t.me/BotFather)

### Step 1 — Get the code onto the server

```bash
git clone <your-repo-url> telebot
cd telebot
```

### Step 2 — Create the production `.env`

Start from the template and adjust these values (the real `.env` is git-ignored, so it is never in the repo):

```bash
cp .env.example .env
```

```env
# --- Core ---
APP_DEBUG=false                      # IMPORTANT: false in production
SECRET_KEY="<long-random-string>"    # generate: python -c "import secrets; print(secrets.token_hex(32))"

# --- Telegram (webhook mode) ---
TELEGRAM_BOT_TOKEN="123456:ABC..."
WEBHOOK_SECRET="<another-random-string>"   # Telegram echoes this in every update
WEBHOOK_URL="https://bot.example.com"      # no trailing slash; no /api/v1/... suffix

# --- LLM ---
OPENROUTER_API_KEY="sk-or-v1-..."

# --- PostgreSQL (strong password!) ---
POSTGRES_USER=assistant
POSTGRES_PASSWORD="<strong-db-password>"
POSTGRES_DB=assistant_agent

# --- Google OAuth (if using calendar) ---
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_REDIRECT_URI="https://bot.example.com/api/v1/auth/google/callback"
```

> On startup, the app automatically registers the webhook at
> `WEBHOOK_URL + /api/v1/telegram/webhook`. Leave `WEBHOOK_URL` empty to
> run in polling mode instead.

### Step 3 — Enable HTTPS

Telegram webhooks **require HTTPS on port 443, 80, 88 or 8443**.

1. Get a certificate (Let's Encrypt is free):

   ```bash
   sudo certbot certonly --standalone -d bot.example.com
   sudo cp /etc/letsencrypt/live/bot.example.com/fullchain.pem nginx/certs/
   sudo cp /etc/letsencrypt/live/bot.example.com/privkey.pem  nginx/certs/
   ```

2. In `docker-compose.yml`, uncomment the certs volume mount:

   ```yaml
   - ./nginx/certs:/etc/nginx/certs:ro
   ```

3. In `nginx/nginx.conf`, uncomment the HTTPS server block and set
   `server_name bot.example.com;`. Optionally enable the HTTP→HTTPS redirect.

> **Quick alternative for testing:** [ngrok](https://ngrok.com) gives you a temporary HTTPS URL:
> `ngrok http 80` → set `WEBHOOK_URL="https://xxxx.ngrok-free.app"`.

### Step 4 — Build and start

```bash
docker compose up --build -d
```

This starts 7 containers:

| Container               | Role                                             |
| ----------------------- | ------------------------------------------------ |
| `assistant-app`         | FastAPI (receives Telegram webhooks, serves API) |
| `assistant-celery`      | Celery worker (background jobs)                  |
| `assistant-celery-beat` | Celery scheduler                                 |
| `assistant-postgres`    | PostgreSQL 16                                    |
| `assistant-redis`       | Redis 7                                          |
| `assistant-qdrant`      | Qdrant vector DB (RAG)                           |
| `assistant-nginx`       | Reverse proxy (80/443) → app                     |

### Step 5 — Verify

```bash
# All containers up?
docker compose ps

# App healthy?
curl http://localhost/api/v1/health

# Webhook registered? (should show your URL and pending_update_count: 0)
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"

# Logs
docker compose logs -f app
```

Then open Telegram and send `/start` to your bot. 🎉

---

## Option B — Deploy without Docker (systemd + local Python)

Useful for a VPS where you can't or don't want to use Docker.

### Step 1 — Install dependencies

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv postgresql redis-server
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
```

(Qdrant optional — the app degrades gracefully without it. Install via its
official binary/docker if you need RAG.)

### Step 2 — Create the database

```bash
sudo -u postgres psql -c "CREATE USER assistant WITH PASSWORD '<strong-password>';"
sudo -u postgres psql -c "CREATE DATABASE assistant_agent OWNER assistant;"
```

Set in `.env`: `POSTGRES_HOST=localhost`, `POSTGRES_USER=assistant`, etc.

### Step 3 — Create a systemd service

`/etc/systemd/system/assistant.service`:

```ini
[Unit]
Description=AI Personal Assistant
After=network.target postgresql.service redis-server.service

[Service]
User=deploy
WorkingDirectory=/home/deploy/telebot
EnvironmentFile=/home/deploy/telebot/.env
ExecStart=/home/deploy/telebot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now assistant
```

Put nginx (or Caddy) in front for TLS, point `WEBHOOK_URL` at it, and
restart. Caddy example (`/etc/caddy/Caddyfile`) gets a certificate automatically:

```
bot.example.com {
    reverse_proxy localhost:8000
}
```

---

## Option C — Quick polling deployment (no domain, no HTTPS)

Run the same stack but in polling mode — Telegram never calls you, so no
public URL is needed:

1. Set `WEBHOOK_URL=""` in `.env` (it already is by default).
2. Add a dedicated poller container to `docker-compose.yml`:

   ```yaml
   poller:
     build: .
     container_name: assistant-poller
     restart: unless-stopped
     env_file:
       - .env
     environment:
       - POSTGRES_HOST=postgres
       - REDIS_HOST=redis
     depends_on:
       postgres:
         condition: service_healthy
     command: python run_dev.py # see note below
   ```

   Note: `run_dev.py` forces SQLite unless you also set
   `DATABASE_URL=postgresql+asyncpg://...` in the poller's environment.

3. `docker compose up -d`, then message your bot.

> ⚠️ Only run **one** poller per bot token. If a webhook is registered,
> polling stops working — clear it with
> `curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"`.

---

## Resetting / Clearing the Database

### SQLite (development mode)

The dev database is a single file - just delete it. Tables are recreated
automatically on the next `python run_dev.py`:

```bash
rm assistant.db        # Linux/macOS
del assistant.db       # Windows
```

### Docker Compose (full wipe - deletes ALL data)

The `-v` flag removes every volume (PostgreSQL, Redis, Qdrant). Users,
chats, documents and vectors are all erased:

```bash
docker compose down -v        # destructive: wipes DB + cache + vectors
docker compose up --build -d  # fresh start
```

### PostgreSQL only (keep Redis/Qdrant data)

Drop and recreate the database, then let the app rebuild the schema
(`create_all` on boot, or `alembic upgrade head`):

```bash
docker compose exec postgres psql -U <POSTGRES_USER> -d postgres \
  -c "DROP DATABASE assistant_agent WITH (FORCE);"
docker compose exec postgres psql -U <POSTGRES_USER> -d postgres \
  -c "CREATE DATABASE assistant_agent OWNER <POSTGRES_USER>;"
docker compose restart app
```

Or keep the schema and just empty the tables:

```bash
docker compose exec postgres psql -U <POSTGRES_USER> -d assistant_agent \
  -c "TRUNCATE messages, chats, users RESTART IDENTITY CASCADE;"
```

### Qdrant only (clear RAG document vectors)

```bash
curl -X DELETE http://localhost:6333/collections/<QDRANT_COLLECTION>
```

The collection is recreated automatically on the next document upload.

---

## Database Migrations

There are currently no Alembic revisions; the app creates any **missing**
tables on startup (`create_all`, idempotent). For schema evolution going
forward, generate and apply migrations:

```bash
# Generate a revision after editing models
docker compose exec app alembic revision --autogenerate -m "describe change"

# Apply
docker compose exec app alembic upgrade head
```

> Do the baseline migration on day one (see "The Expert Path", Decision 2)
> so future model changes are always manageable.

---

## Operations Cheat Sheet

```bash
docker compose up -d                # start / apply changes
docker compose up --build -d        # rebuild after code changes
docker compose logs -f app          # tail app logs
docker compose logs -f celery_worker
docker compose restart app          # restart one service
docker compose down                 # stop (keeps volumes/data)
docker compose down -v              # stop AND DELETE DATA ⚠️

# Re-register webhook after changing WEBHOOK_URL
docker compose restart app

# Check Telegram's view of your bot
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Renew certs (cron: monthly) and reload nginx
sudo certbot renew && docker compose exec nginx nginx -s reload
```

### Updating to a new version

```bash
git pull
docker compose up --build -d
docker compose exec app alembic upgrade head
```

---

## Security Checklist ✅

- [ ] `APP_DEBUG=false` in production
- [ ] `SECRET_KEY` and `WEBHOOK_SECRET` are long random strings (not the committed defaults)
- [ ] `.env` is **never** committed (already in `.gitignore`); `chmod 600 .env` on the server
- [ ] Strong `POSTGRES_PASSWORD`; DB/Redis/Qdrant ports bound to `127.0.0.1` only (done in compose)
- [ ] UFW/firewall: only 22/80/443 open
- [ ] HTTPS enabled for the webhook endpoint
- [ ] Rotate any tokens that were previously committed or shared

---

## Troubleshooting 🔧

| Symptom                                  | Likely cause / fix                                                                                                                             |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Bot never replies                        | `getWebhookInfo` shows `url: ""` → `WEBHOOK_URL` empty while running webhook mode; or a poller isn't running. Check `docker compose logs app`. |
| `last_error_message` in `getWebhookInfo` | Telegram can't reach you: DNS wrong, port 443 blocked, or cert invalid.                                                                        |
| `403 Forbidden` on webhook               | `WEBHOOK_SECRET` in `.env` doesn't match the one used at registration → restart app to re-register.                                            |
| Webhook + polling conflict               | Only one works at a time. `deleteWebhook` before polling; set `WEBHOOK_URL` before webhooks.                                                   |
| App crash on boot                        | Check `docker compose logs app` — usually a bad `DATABASE_URL`, Postgres not healthy, or missing env var.                                      |
| Webhook works, bot silent                | Verify `WEBHOOK_URL` uses port 443 (Telegram only supports 443/80/88/8443) and no trailing slash/path mistakes.                                |
| Google OAuth fails in prod               | `GOOGLE_REDIRECT_URI` must exactly match the authorized redirect URI in Google Cloud Console.                                                  |
