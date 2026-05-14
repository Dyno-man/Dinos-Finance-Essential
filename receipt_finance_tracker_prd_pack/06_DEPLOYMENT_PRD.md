# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

# VPS Deployment Product Requirements Document

## 1. Purpose

Deploy Receipt Finance Tracker on a VPS using Docker, Nginx, PostgreSQL, persistent volumes, environment variables, HTTPS, and backups.

## 2. Production Services

1. `web`
   1. Next.js app.
   2. Exposed only through Nginx.

2. `api`
   1. FastAPI API based on informationHandler.
   2. Internal plus Nginx routed API paths.

3. `ocr`
   1. FastAPI OCR image processor based on imageContainer.
   2. Internal only.
   3. Not exposed directly to public internet.

4. `worker`
   1. Background ingestion jobs.
   2. Gmail scheduled ingestion.
   3. Telegram processing and retries.

5. `db`
   1. PostgreSQL.
   2. Persistent volume.

7. `nginx`
   1. Public port 80 and 443.
   2. HTTPS.
   3. Reverse proxy.

## 3. Docker Compose Production Requirements

1. Use explicit service names.
2. Use internal Docker network.
3. Expose only Nginx publicly.
4. Do not expose PostgreSQL publicly.
5. Do not expose OCR service publicly.
6. Persist database data.
7. Persist uploaded receipt files.
8. Persist Telegram mappings in PostgreSQL.
9. Use `.env` for secrets.
10. Use restart policy `unless-stopped`.

## 4. Environment Variables

Required:

```text
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=
JWT_SECRET=
COOKIE_SECRET=
APP_BASE_URL=
API_BASE_URL=
OCR_SERVICE_URL=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID_PRO=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GMAIL_TOKEN_ENCRYPTION_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_REPLY_ENABLED=
RECEIPT_STORAGE_PATH=
MAX_UPLOAD_MB=
```

## 5. Nginx Routing

Routes:

1. `/` goes to `web`.
2. `/api/` goes to `api`.
3. `/billing/webhook` goes to `api`.
4. Internal service routes are not exposed.

Requirements:

1. HTTPS enabled.
2. HTTP redirects to HTTPS.
3. Upload body size supports receipt images.
4. Security headers enabled.
5. Access logs enabled.

## 6. Backup Requirements

Back up:

1. PostgreSQL database.
2. Receipt upload volume.
3. `.env` stored securely outside repo.

Backup frequency:

1. Database daily.
2. Receipt files daily.
3. Before deployment migrations.

Restore test:

1. Monthly restore test recommended.
2. Document restore commands.

## 7. Logging Requirements

1. API structured logs.
2. Worker job logs.
3. OCR processing logs.
4. Nginx access and error logs.
5. Stripe webhook logs without sensitive payload dumps.
6. Gmail ingestion logs without full message bodies.
7. Telegram logs without full attachment contents.

## 8. Health Checks

Health endpoints:

1. `web` returns page.
2. `api` GET `/health`.
3. `ocr` GET `/health`.
4. `worker` writes heartbeat row or exposes health endpoint.
5. `db` PostgreSQL health check.

Admin health page should show:

1. API status.
2. OCR status.
3. Database status.
4. Worker last heartbeat.
5. Last Gmail ingestion.
6. Telegram webhook status.
7. Failed jobs count.

## 9. Migration Requirements

Use Alembic or equivalent.

Rules:

1. Schema changes must be migrations.
2. Run migrations before starting new app version.
3. Never manually edit production schema without migration.
4. Seed default categories.

## 10. Deployment Flow

1. Pull latest repo.
2. Build images.
3. Run tests.
4. Run database backup.
5. Run migrations.
6. Start containers.
7. Check health page.
8. Test upload flow.
9. Test login.
10. Test Stripe webhook in test mode.

## 11. Acceptance Criteria

1. App is reachable through HTTPS.
2. PostgreSQL is not public.
3. OCR service is not public.
4. Uploads persist across restarts.
5. Database persists across restarts.
6. Telegram mappings persist across restarts.
7. Restarting containers does not lose receipt data.
8. Backups can be created with one command.
9. Admin can see service health.
