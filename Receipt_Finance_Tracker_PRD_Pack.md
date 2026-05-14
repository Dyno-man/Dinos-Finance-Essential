

<!-- 00_MASTER_PRD.md -->


# Receipt Finance Tracker Master Product Requirements Document

## 1. Product Summary

Receipt Finance Tracker is a self hosted receipt ingestion and spending dashboard application. The current repository already has the core OCR direction in place: a FastAPI image processing container reads uploaded receipt images, extracts text through EasyOCR, finds a total value, and returns the detected cost. A second FastAPI information handler forwards uploaded images to the OCR service. PostgreSQL is already present in the Docker compose plan.

The finished product should become a full web app where users can create accounts, upload receipts, text receipts through a Telegram bot, connect Gmail receipt folders, review extracted receipt data, correct OCR mistakes, and view spending analytics by date, merchant, category, and source.

## 2. Primary Goals

1. Preserve the current backend direction instead of replacing it.
2. Build a production ready web front end around the receipt tracker.
3. Add user accounts using username and password authentication.
4. Store receipts in a scalable multi user PostgreSQL schema.
5. Support multiple receipt sources:
   1. Web upload.
   2. Telegram bot image upload.
   3. Gmail receipt inbox ingestion.
6. Add Stripe subscription billing so other users can sign up.
7. Deploy the full system on a VPS using Docker, Nginx, HTTPS, background jobs, and backups.
8. Keep OCR outputs editable because the current OCR model is useful but not perfect.

## 3. Non Goals For Version 1

1. Direct bank account linking.
2. Full accounting software replacement.
3. Tax filing automation.
4. Native mobile apps.
5. Automatic category prediction that cannot be corrected by the user.
6. Storing full payment card numbers or sensitive payment data inside this app.

## 4. Current Repository Context

The repo currently contains these important pieces:

1. `imageContainer`
   1. FastAPI service.
   2. Uses EasyOCR and Pillow.
   3. Accepts image uploads.
   4. Saves uploaded image temporarily.
   5. Runs OCR.
   6. Searches extracted text for a number near the word total.
   7. Returns the detected cost.

2. `informationHandler`
   1. FastAPI service.
   2. Accepts image uploads.
   3. Validates that the upload can be opened as an image.
   4. Forwards the image to the image container.
   5. Returns OCR output to the caller.
   6. Has `psycopg` in requirements, so this service is the right place to write receipt records to PostgreSQL.

3. `compose.yaml`
   1. Runs backend image processor.
   2. Runs middleware or information handler.
   3. Runs PostgreSQL.
   4. Uses environment variables for database credentials.
   5. Uses a persistent volume for PostgreSQL.

4. `Artifacts.md`
   1. Early table design includes ReceiptID, Date, Type of Expense, and Amount.
   2. The finished version should expand this into a real multi user schema.

## 5. User Personas

### 5.1 Individual User

A user wants to track spending by uploading physical receipts, forwarding email receipts, or texting receipt images to a Telegram number. They want the least manual work possible, but they still need the ability to correct OCR mistakes.

### 5.2 Power User

A user wants monthly trends, categories, exportable data, and repeat merchant behavior. They care about reliability and automation.

### 5.3 Admin

The app owner needs to manage users, subscriptions, ingestion health, failed OCR jobs, and storage usage.

## 6. Core User Flows

### 6.1 Web Receipt Upload

1. User signs in.
2. User opens dashboard.
3. User uploads receipt image.
4. Front end sends file to the API.
5. API stores receipt image metadata and creates a processing job.
6. OCR service extracts text and total.
7. API stores extracted result.
8. User reviews parsed merchant, date, total, category, and line items if available.
9. User saves corrections.
10. Dashboard updates analytics.

### 6.2 Telegram Receipt Upload

1. User signs in.
2. User opens integrations.
3. User links their Telegram account with `/start CODE`.
4. User sends a receipt image to their assigned Telegram bot number or linked Telegram identity.
5. Telegram listener receives the message and attachment.
6. Backend maps Telegram sender to the correct app user.
7. Backend creates receipt record with source `telegram`.
8. OCR processes the image.
9. User receives confirmation message with detected total and review link.

### 6.3 Gmail Receipt Ingestion

1. User signs in.
2. User opens integrations.
3. User connects Gmail through OAuth.
4. User chooses a Gmail label, default `Receipts`.
5. User chooses a schedule, default daily.
6. Scheduled job searches Gmail for unread or unprocessed messages in that label.
7. Backend downloads receipt attachments or extracts receipt HTML text.
8. Backend creates receipt records with source `gmail`.
9. Successfully processed messages are marked or labeled as processed.
10. Failed messages are logged and visible in the app.

### 6.4 Subscription Signup

1. New user creates account.
2. User chooses free or paid plan.
3. Paid plan opens Stripe Checkout.
4. Stripe confirms payment through webhook.
5. Backend activates user subscription.
6. App enforces plan limits.

## 7. MVP Scope

### Must Have

1. Account creation and login.
2. Protected dashboard.
3. Upload receipt image from web.
4. Receipt list page.
5. Receipt detail page with editable extracted fields.
6. Spending summary cards.
7. Category breakdown chart.
8. Monthly spending chart.
9. PostgreSQL multi user schema.
10. OCR processing job status.
11. Basic Telegram ingestion.
12. Basic Gmail daily ingestion.
13. Stripe Checkout and subscription webhook.
14. Docker compose production deployment.
15. Nginx reverse proxy with HTTPS.
16. Environment variable based config.
17. Basic admin health page.

### Should Have

1. Merchant detection.
2. Receipt image preview.
3. Manual category override.
4. Search and filters.
5. CSV export.
6. Email ingestion failure retry.
7. Telegram confirmation message.
8. Plan usage limits.

### Could Have

1. Line item extraction.
2. Budget alerts.
3. Multi currency support.
4. Browser notification when OCR is complete.
5. Team or household accounts.

## 8. Success Metrics

1. User can create account and upload a receipt in under 60 seconds.
2. At least 95 percent of supported image uploads create a receipt record.
3. OCR result appears within 15 seconds for normal receipt images.
4. User can correct any OCR field before it affects analytics.
5. Gmail ingestion can process a daily receipt label without duplicates.
6. Telegram ingestion correctly maps messages to the right user.
7. Stripe webhook reliably updates subscription status.
8. VPS deployment can restart containers without losing data.

## 9. Main Data Objects

1. User.
2. Account session.
3. Subscription.
4. Receipt.
5. Receipt image.
6. OCR result.
7. Expense category.
8. Integration connection.
9. Telegram sender mapping.
10. Gmail connection.
11. Gmail processed message.
12. Ingestion job.
13. Audit log.

## 10. Recommended Build Order

1. Refactor backend API boundaries and database schema.
2. Add authentication and user ownership.
3. Build front end shell and dashboard.
4. Build web upload receipt flow.
5. Add receipt review and edit flow.
6. Add analytics pages.
7. Add Telegram ingestion.
8. Add Gmail ingestion.
9. Add Stripe subscriptions.
10. Add production VPS deployment hardening.

## 11. Acceptance Criteria

1. No receipt data can be accessed without authentication.
2. Users can only see their own receipts.
3. Every created receipt has a source field.
4. Every OCR result stores both raw text and parsed fields.
5. Every parsed field can be manually corrected.
6. Deleting a receipt removes it from analytics.
7. Gmail and Telegram ingestion are idempotent and do not create duplicates.
8. Stripe subscription state is based on webhooks, not front end trust.
9. The app can be deployed with one documented Docker compose production command.


<!-- 01_ARCHITECTURE_AND_DATA_PRD.md -->


# Architecture And Data Product Requirements Document

## 1. Purpose

This document defines the backend, service boundaries, database schema, API contracts, and job flow required to turn the current OCR prototype into a scalable app.

## 2. Existing Architecture To Preserve

The current repo already separates image processing from request handling:

1. `imageContainer`
   1. Responsible for OCR.
   2. Should remain stateless.
   3. Should receive files, process them, and return structured OCR output.

2. `informationHandler`
   1. Responsible for accepting outside requests.
   2. Should become the main API service.
   3. Should own database writes.
   4. Should call the OCR service.
   5. Should enforce authentication, user ownership, and integration rules.

3. PostgreSQL
   1. Stores users.
   2. Stores receipts.
   3. Stores integrations.
   4. Stores job state.
   5. Stores subscription state.

## 3. Recommended Final Services

1. `web`
   1. Next.js front end.
   2. Server side routes only when needed for auth and Stripe.
   3. Talks to `api`.

2. `api`
   1. FastAPI service based on `informationHandler`.
   2. Auth, receipt CRUD, upload, integrations, jobs, analytics.
   3. Talks to PostgreSQL and OCR service.

3. `ocr`
   1. FastAPI service based on `imageContainer`.
   2. EasyOCR model loaded once at startup.
   3. Receives file bytes.
   4. Returns raw OCR text and parsed fields.

4. `worker`
   1. Background job processor.
   2. Handles Gmail scheduled ingestion.
   3. Handles Telegram message ingestion if not event driven.
   4. Handles OCR retry jobs.
   5. Can be built as a separate FastAPI worker process or a Python script container.

5. `telegram`
   1. Telegram Bot API webhook.
   2. Receives and sends Telegram messages.
   3. Stores attachments temporarily.

6. `db`
   1. PostgreSQL.

7. `nginx`
   1. Reverse proxy.
   2. HTTPS termination.
   3. Routes app domain to web and API.

## 4. Database Schema

### 4.1 users

Purpose: app account ownership.

Fields:

1. id UUID primary key.
2. username text unique not null.
3. email text unique nullable.
4. password_hash text not null.
5. role text not null default `user`.
6. created_at timestamptz not null.
7. updated_at timestamptz not null.
8. disabled_at timestamptz nullable.

### 4.2 subscriptions

Purpose: Stripe subscription state.

Fields:

1. id UUID primary key.
2. user_id UUID references users.
3. stripe_customer_id text unique nullable.
4. stripe_subscription_id text unique nullable.
5. plan_name text not null default `free`.
6. status text not null default `free`.
7. current_period_end timestamptz nullable.
8. cancel_at_period_end boolean not null default false.
9. created_at timestamptz not null.
10. updated_at timestamptz not null.

### 4.3 receipts

Purpose: canonical expense record.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. source text not null.
4. source_external_id text nullable.
5. merchant_name text nullable.
6. purchased_at timestamptz nullable.
7. amount_cents integer nullable.
8. currency text not null default `USD`.
9. category_id UUID nullable references categories.
10. status text not null default `pending_review`.
11. notes text nullable.
12. created_at timestamptz not null.
13. updated_at timestamptz not null.
14. deleted_at timestamptz nullable.

Constraints:

1. source must be one of `web`, `telegram`, `gmail`, `manual`.
2. status must be one of `processing`, `pending_review`, `confirmed`, `failed`.
3. Unique nullable duplicate prevention index on user_id, source, source_external_id where source_external_id is not null.

### 4.4 receipt_images

Purpose: store image metadata and file location.

Fields:

1. id UUID primary key.
2. receipt_id UUID references receipts not null.
3. storage_path text not null.
4. original_filename text nullable.
5. mime_type text nullable.
6. size_bytes integer nullable.
7. sha256 text not null.
8. created_at timestamptz not null.

### 4.5 ocr_results

Purpose: store raw and parsed OCR output.

Fields:

1. id UUID primary key.
2. receipt_id UUID references receipts not null.
3. raw_text text not null.
4. raw_blocks jsonb nullable.
5. parsed_total_cents integer nullable.
6. parsed_date timestamptz nullable.
7. parsed_merchant text nullable.
8. parser_version text not null.
9. confidence numeric nullable.
10. created_at timestamptz not null.

### 4.6 categories

Purpose: user editable expense categories.

Fields:

1. id UUID primary key.
2. user_id UUID references users nullable.
3. name text not null.
4. color text nullable.
5. is_default boolean not null default false.
6. created_at timestamptz not null.

Seed default categories:

1. Grocery.
2. Automobile.
3. Restaurant.
4. Recreation.
5. Household.
6. Health.
7. Other.

### 4.7 integration_connections

Purpose: one table for connected services.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. provider text not null.
4. status text not null default `active`.
5. display_name text nullable.
6. created_at timestamptz not null.
7. updated_at timestamptz not null.

Provider values:

1. `telegram`.
2. `gmail`.

### 4.8 telegram_mappings

Purpose: map Telegram bot users to app users.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. telegram_user_id text nullable unique
4. telegram_chat_id text nullable
5. telegram_username text nullable.
4. linked_at timestamptz not null.
5. verified_at timestamptz nullable.
6. verification_code_hash text nullable.

### 4.9 gmail_connections

Purpose: store Gmail OAuth and ingestion settings.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. google_email text not null.
4. encrypted_refresh_token text not null.
5. receipt_label text not null default `Receipts`.
6. processed_label text not null default `ReceiptTrackerProcessed`.
7. ingestion_time_local time not null default `02:00`.
8. timezone text not null default `America/New_York`.
9. last_history_id text nullable.
10. created_at timestamptz not null.
11. updated_at timestamptz not null.

### 4.10 gmail_processed_messages

Purpose: prevent duplicate email ingestion.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. gmail_message_id text not null.
4. gmail_thread_id text nullable.
5. receipt_id UUID references receipts nullable.
6. processed_at timestamptz not null.
7. status text not null.
8. error_message text nullable.

Unique constraint:

1. user_id plus gmail_message_id.

### 4.11 ingestion_jobs

Purpose: track processing from all sources.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. receipt_id UUID references receipts nullable.
4. source text not null.
5. job_type text not null.
6. status text not null default `queued`.
7. attempts integer not null default 0.
8. error_message text nullable.
9. run_after timestamptz not null default now.
10. created_at timestamptz not null.
11. updated_at timestamptz not null.

## 5. OCR API Contract

### POST `/ocr/upload`

Request:

1. multipart file field named `file`.

Response:

```json
{
  "raw_text": ["WALMART", "TOTAL", "12.34"],
  "parsed": {
    "total_cents": 1234,
    "merchant_name": "WALMART",
    "purchased_at": null
  },
  "confidence": null,
  "parser_version": "easyocr_total_v1"
}
```

Rules:

1. OCR service should not write to the database.
2. OCR service should not know user IDs.
3. OCR service should remove temporary files after processing.
4. OCR service should validate MIME type and file size.
5. OCR service should return errors in a structured format.

## 6. Main API Endpoints

### Auth

1. POST `/auth/register`.
2. POST `/auth/login`.
3. POST `/auth/logout`.
4. GET `/auth/me`.

### Receipts

1. POST `/receipts/upload`.
2. GET `/receipts`.
3. GET `/receipts/{id}`.
4. PATCH `/receipts/{id}`.
5. DELETE `/receipts/{id}`.
6. POST `/receipts/{id}/confirm`.
7. POST `/receipts/{id}/reprocess`.

### Analytics

1. GET `/analytics/summary`.
2. GET `/analytics/monthly`.
3. GET `/analytics/categories`.
4. GET `/analytics/merchants`.

### Integrations

1. GET `/integrations`.
2. POST `/integrations/telegram/link`.
3. DELETE `/integrations/telegram`.
4. GET `/integrations/gmail/start`.
5. GET `/integrations/gmail/callback`.
6. PATCH `/integrations/gmail/settings`.
7. POST `/integrations/gmail/run-now`.

### Billing

1. POST `/billing/create-checkout-session`.
2. POST `/billing/create-portal-session`.
3. POST `/billing/webhook`.

### Admin

1. GET `/admin/health`.
2. GET `/admin/jobs`.
3. POST `/admin/jobs/{id}/retry`.

## 7. Receipt Upload Flow

1. User uploads file to `/receipts/upload`.
2. API validates auth.
3. API validates file type and size.
4. API computes SHA256.
5. API stores file.
6. API creates receipt with status `processing`.
7. API calls OCR service.
8. API stores OCR result.
9. API updates receipt fields.
10. API sets status `pending_review`.
11. API returns receipt ID and parsed fields.

## 8. Storage Requirements

For MVP, use local VPS filesystem storage with mounted Docker volume:

1. `/data/receipt_uploads/{user_id}/{receipt_id}/original.ext`.

Future compatible abstraction:

1. Implement a storage service interface so local storage can later move to S3 compatible object storage.

## 9. Security Requirements

1. Passwords must be hashed with Argon2id or bcrypt.
2. Access tokens must be HTTP only secure cookies.
3. User ownership must be checked on every receipt route.
4. Uploaded files must have size limits.
5. Uploaded files must be decoded as images before processing.
6. Temporary files must be removed.
7. OAuth tokens must be encrypted at rest.
8. Stripe webhooks must verify Stripe signatures.
9. Telegram webhook endpoints must reject unauthorized internal requests.
10. API should apply request rate limits to auth and upload endpoints.

## 10. Acceptance Criteria

1. A receipt uploaded through the web creates exactly one receipt row.
2. OCR raw text is always stored.
3. The app never trusts the OCR result as final until user review.
4. A failed OCR job marks receipt as `failed` and shows an error.
5. Retrying a failed job does not create duplicate receipts.
6. Gmail message IDs cannot be processed twice for the same user.
7. Telegram user ID maps to exactly one app user.
8. Deleting a user disables login and prevents new ingestion.


<!-- 02_FRONTEND_PRD.md -->


# Front End Product Requirements Document

## 1. Purpose

Build a polished Next.js front end for Receipt Finance Tracker that matches the product already described in the repo: upload receipt images, store extracted costs, and show graphs and tables that explain spending.

## 2. Design Direction

The app should feel like a clean personal finance dashboard, not a generic admin panel. It should be simple enough for one person tracking receipts but scalable enough for paid users.

Style goals:

1. Dark and light mode friendly.
2. Clean cards.
3. Clear spending totals.
4. Minimal visual clutter.
5. Strong receipt review workflow.
6. Mobile usable, especially for uploading receipt pictures.

## 3. Navigation

Main navigation:

1. Dashboard.
2. Receipts.
3. Upload.
4. Analytics.
5. Integrations.
6. Billing.
7. Settings.

Admin navigation, visible only to admin users:

1. Health.
2. Jobs.
3. Users.

## 4. Pages

### 4.1 Landing Page

Purpose: explain the product and convert visitors.

Sections:

1. Hero.
2. How it works.
3. Upload, Telegram, Gmail ingestion cards.
4. Dashboard preview.
5. Pricing.
6. Sign up call to action.

Acceptance criteria:

1. User can click Sign up.
2. User can click Login.
3. Page explains that OCR output can be corrected.
4. Page does not claim perfect receipt extraction.

### 4.2 Register Page

Fields:

1. Username.
2. Email, optional if backend allows.
3. Password.
4. Confirm password.

Validation:

1. Username required.
2. Password minimum 12 characters recommended.
3. Confirm password must match.
4. Show friendly errors.

### 4.3 Login Page

Fields:

1. Username or email.
2. Password.

Acceptance criteria:

1. Successful login redirects to dashboard.
2. Invalid login shows generic error.
3. No password is ever logged to console.

### 4.4 Dashboard Page

Top cards:

1. This month spending.
2. Number of receipts this month.
3. Average receipt amount.
4. Receipts pending review.

Main sections:

1. Monthly spend chart.
2. Category breakdown chart.
3. Recent receipts table.
4. Ingestion status summary.

Acceptance criteria:

1. Empty state is useful for new users.
2. Data only comes from authenticated user.
3. Pending review receipts are clearly visible.

### 4.5 Upload Page

Features:

1. Drag and drop image upload.
2. File picker.
3. Mobile camera friendly input.
4. Upload progress.
5. Processing status.
6. Redirect to receipt review when done.

Accepted file types:

1. JPG.
2. PNG.
3. WebP.
4. PDF only if backend supports it later.

Acceptance criteria:

1. Invalid file type shows an error before upload.
2. Large files are rejected with clear message.
3. User sees OCR processing state.
4. Upload never blocks the entire UI.

### 4.6 Receipts List Page

Filters:

1. Date range.
2. Category.
3. Merchant.
4. Source.
5. Status.
6. Minimum and maximum amount.

Table columns:

1. Date.
2. Merchant.
3. Amount.
4. Category.
5. Source.
6. Status.
7. Actions.

Actions:

1. View.
2. Edit.
3. Delete.

Acceptance criteria:

1. Pagination or infinite scroll exists.
2. Search is debounced.
3. Deleted receipts disappear from default view.
4. Pending review status is visually obvious.

### 4.7 Receipt Detail And Review Page

Sections:

1. Receipt image preview.
2. OCR raw text.
3. Editable parsed fields.
4. Category selector.
5. Source metadata.
6. Save and confirm buttons.
7. Reprocess button.

Editable fields:

1. Merchant.
2. Purchase date.
3. Total amount.
4. Category.
5. Notes.

Acceptance criteria:

1. User can correct the total.
2. User can correct the merchant.
3. User can confirm the receipt.
4. Confirmed receipt affects analytics.
5. Failed receipt can be reprocessed.
6. Raw OCR text remains visible for debugging.

### 4.8 Analytics Page

Charts:

1. Spending by month.
2. Spending by category.
3. Spending by merchant.
4. Receipts by source.
5. Pending review count over time, optional.

Controls:

1. Date range.
2. Category filter.
3. Source filter.

Acceptance criteria:

1. Charts handle zero data.
2. Amounts are displayed as currency.
3. Category totals match receipt list totals for same filters.

### 4.9 Integrations Page

Sections:

1. Telegram.
2. Gmail.
3. Future banking API placeholder, disabled.

Telegram section:

1. Show linked Telegram number if connected.
2. Button to start linking.
3. Instructions for texting a receipt.
4. Test message button if supported.

Gmail section:

1. Connect Gmail button.
2. Label name setting.
3. Daily ingestion time setting.
4. Last run status.
5. Run now button.
6. Disconnect button.

Acceptance criteria:

1. Connected services show status.
2. Failed integrations show helpful error.
3. User can disconnect an integration.

### 4.10 Billing Page

Sections:

1. Current plan.
2. Usage this month.
3. Upgrade button.
4. Manage billing button.
5. Billing status message.

Acceptance criteria:

1. Free users can upgrade.
2. Paid users can open Stripe customer portal.
3. Subscription status updates after webhook sync.

### 4.11 Settings Page

Sections:

1. Profile.
2. Password.
3. Categories.
4. Data export.
5. Delete account.

Acceptance criteria:

1. User can create custom categories.
2. User can rename categories.
3. User can export CSV.
4. Account deletion requires confirmation.

## 5. Front End Components

1. AppShell.
2. Sidebar.
3. TopNav.
4. StatCard.
5. ReceiptUploadDropzone.
6. ReceiptTable.
7. ReceiptStatusBadge.
8. CategorySelect.
9. CurrencyInput.
10. ReceiptImageViewer.
11. OCRRawTextPanel.
12. DateRangePicker.
13. IntegrationCard.
14. BillingPlanCard.
15. EmptyState.
16. ErrorState.
17. LoadingSkeleton.

## 6. API Client Requirements

1. Centralize API calls in `/lib/api`.
2. Include auth credentials automatically.
3. Handle 401 by redirecting to login.
4. Show toast errors for expected failures.
5. Never expose secrets in front end code.

## 7. State Management

Use simple React state and server data fetching first.

Recommended:

1. Server components for initial page data where practical.
2. React Query or SWR for client side mutation and refetching.
3. URL search params for filters.

## 8. Accessibility Requirements

1. Every form input has a label.
2. Upload area works with keyboard.
3. Buttons have clear text.
4. Charts have table fallback or summary text.
5. Color is not the only status indicator.

## 9. Codex Task Prompt

Use this prompt in Codex:

```text
You are working in the Receipt Finance Tracker repository. Build a production ready Next.js front end for the existing receipt OCR backend. Preserve the current product direction from the README: users upload receipts, OCR extracts totals, receipts are stored, and charts and tables explain spending.

Create a Next.js app with TypeScript. Implement pages for landing, register, login, dashboard, upload, receipts list, receipt detail review, analytics, integrations, billing, and settings. Use a clean finance dashboard design with cards, tables, charts, and mobile friendly upload. Do not hardcode fake backend behavior except temporary mock data behind clearly named mock functions.

Use a central API client. Include authentication aware routing. Build reusable components for receipt tables, upload dropzone, OCR raw text panel, category selector, and spending charts. Make OCR fields editable because the OCR model is not perfect. Keep all code organized and documented.
```


<!-- 03_TELEGRAM_BOT_PRD.md -->


# Telegram Bot Integration Product Requirements Document

## 1. Purpose

Allow each user to send receipt images directly to the app through a Telegram bot. The app should process the image with the existing OCR pipeline, save the receipt under the correct user, and optionally send a confirmation reply through Telegram.

## 2. Integration Approach

Use the official Telegram Bot API. Telegram delivers updates to a public webhook endpoint protected by Telegram's webhook secret token. The app downloads image files from Telegram with the configured bot token and does not run a separate bridge service.

Recommended design:

1. Create a Telegram bot through BotFather.
2. Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`.
3. Register the backend `/telegram/webhook` URL with Telegram using the same secret token.
4. Link users with a `/start CODE` flow.
5. Map Telegram user and chat IDs to app users.
6. Process incoming photo or image document attachments as receipt uploads.
7. Send confirmation messages back to the Telegram chat.

## 3. User Flow

### 3.1 Link Telegram Account

1. User signs in.
2. User opens Integrations.
3. User selects Connect Telegram.
4. App generates a verification code.
5. User sends `/start CODE` to the Telegram bot.
6. Telegram calls the app webhook.
7. App verifies the code.
8. App stores Telegram user ID, chat ID, and optional username as linked.

### 3.2 Upload Receipt Through Telegram

1. User sends a receipt photo or image document to the bot.
2. Telegram calls the webhook with the message update.
3. Backend downloads the image from Telegram.
4. Backend creates a receipt with source `telegram`.
5. OCR service extracts raw text and total.
6. Backend stores OCR result.
7. Backend sends reply:
   `Receipt received. I found $12.34. Review it here: <link>`

### 3.3 Failure Flow

1. User sends unsupported file.
2. App responds:
   `I could not process that file. Please send a JPG, PNG, or WebP receipt image.`
3. Failure is logged against the Telegram update.

## 4. Requirements

### Must Have

1. Telegram connection status on integrations page.
2. `/start CODE` verification.
3. Incoming photo and image document support.
4. Mapping from Telegram sender to user.
5. Receipt creation with source `telegram`.
6. OCR processing through existing OCR service.
7. Duplicate prevention based on Telegram update ID or attachment hash.
8. Confirmation reply after successful receipt creation.
9. Friendly error reply after failure.

### Should Have

1. Support multiple images in one message.
2. Support text like `category grocery`.
3. Allow user to text `help`.
4. Allow user to text `unlink`.
5. Admin page for Telegram webhook health.

### Could Have

1. Natural language corrections by text.
2. Monthly spending summaries over Telegram.
3. Budget alerts over Telegram.

## 5. Backend Endpoints

### POST `/integrations/telegram/link`

Request:

```json
{}
```

Response:

```json
{
  "status": "pending_verification",
  "message": "Send /start 123456 to the Telegram bot."
}
```

### POST `/telegram/webhook`

Webhook endpoint called by Telegram. Requests must include `X-Telegram-Bot-Api-Secret-Token`.

Request shape follows Telegram's update object. The app handles private-message updates containing `text`, `photo`, or image `document` payloads.

Response:

```json
{
  "status": "accepted",
  "created_receipts": ["receipt_uuid"]
}
```

## 6. Database Additions

Use the `telegram_mappings` table from the architecture PRD.

Add optional table `telegram_messages`:

1. id UUID primary key.
2. user_id UUID references users nullable.
3. telegram_update_id integer not null unique.
4. telegram_message_id integer nullable.
5. telegram_chat_id text nullable.
6. telegram_user_id text nullable.
7. raw_payload jsonb not null.
8. processed_at timestamptz nullable.
9. status text not null.
10. error_message text nullable.
11. created_at timestamptz not null.

## 7. Security Requirements

1. Webhook must validate Telegram's secret token header.
2. Never log full message attachment contents.
3. Never expose linked Telegram IDs to other users.
4. Store only needed Telegram metadata.
5. Allow user to unlink Telegram.
6. Rate limit messages per sender.
7. Validate file type and size before OCR.

## 8. Docker Compose Requirements

No Telegram service is required. The API service needs:

```yaml
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_REPLY_ENABLED=true
```

## 9. Acceptance Criteria

1. User can link a Telegram account with `/start CODE`.
2. User can send a receipt image by Telegram.
3. App creates a receipt owned by that user.
4. Receipt source is `telegram`.
5. OCR result is stored.
6. User receives a confirmation message.
7. Duplicate Telegram updates do not create duplicate receipts.
8. Unknown senders receive a linking instruction.


<!-- 04_GMAIL_INGESTION_PRD.md -->


# Gmail Receipt Ingestion Product Requirements Document

## 1. Purpose

Allow users to connect Gmail and have the app read receipt emails from a chosen label on a daily schedule. The goal is to support the user's plan of creating a Gmail rule that places receipts into a receipt inbox or receipt label.

## 2. Recommended Gmail Model

Use OAuth to connect each user's Gmail account. Users should create a Gmail label such as `Receipts`, then use Gmail filters to automatically apply that label to receipt emails. The app will search that label on a schedule and process messages that have not been processed before.

Version 1 should use scheduled polling because the user specifically wants the app to read the receipt inbox at a specific time each day. Push notifications can be added later.

## 3. User Flow

### 3.1 Connect Gmail

1. User signs in.
2. User opens Integrations.
3. User clicks Connect Gmail.
4. User completes Google OAuth consent.
5. App stores encrypted refresh token.
6. User chooses label name, default `Receipts`.
7. User chooses daily ingestion time.
8. User saves settings.

### 3.2 Daily Receipt Import

1. Worker finds Gmail connections due for ingestion.
2. Worker refreshes access token.
3. Worker searches messages with the configured label.
4. Worker skips messages already stored in `gmail_processed_messages`.
5. Worker reads message metadata and payload.
6. Worker extracts image or PDF attachments if available.
7. Worker extracts HTML or plain text body if no attachment exists.
8. Worker creates receipt record with source `gmail`.
9. Worker sends image attachment to OCR service when applicable.
10. Worker stores parsed email text and OCR text.
11. Worker labels or marks the message as processed.
12. Worker records success or failure.

## 4. Supported Email Inputs

### Must Have

1. Image attachments.
2. PDF attachment placeholder with graceful failure unless PDF support is implemented.
3. HTML receipt body text.
4. Plain text receipt body text.

### Should Have

1. Multiple attachments in one email.
2. Merchant detection from sender or subject.
3. Amount extraction from email body.
4. Duplicate prevention by Gmail message ID.

## 5. Gmail Search Strategy

Default search query:

```text
label:Receipts
```

Optional query additions:

```text
has:attachment
newer_than:30d
```

Do not rely only on unread status because users may read receipt emails before ingestion.

## 6. Backend Endpoints

### GET `/integrations/gmail/start`

Starts OAuth.

### GET `/integrations/gmail/callback`

Handles OAuth callback.

### PATCH `/integrations/gmail/settings`

Request:

```json
{
  "receipt_label": "Receipts",
  "processed_label": "ReceiptTrackerProcessed",
  "ingestion_time_local": "02:00",
  "timezone": "America/New_York"
}
```

### POST `/integrations/gmail/run-now`

Manually triggers ingestion for the current user.

### GET `/integrations/gmail/status`

Returns:

```json
{
  "connected": true,
  "google_email": "user@gmail.com",
  "receipt_label": "Receipts",
  "last_run_at": "2026-05-12T06:00:00Z",
  "last_status": "success"
}
```

## 7. Worker Requirements

1. Runs every 5 minutes to check due Gmail ingestion schedules.
2. Processes each user's Gmail connection independently.
3. Uses idempotency based on Gmail message ID.
4. Logs all failures to ingestion jobs.
5. Retries temporary failures.
6. Does not retry permanent permission failures forever.
7. Supports manual run now.

## 8. Database Requirements

Use these tables from the architecture PRD:

1. `gmail_connections`.
2. `gmail_processed_messages`.
3. `ingestion_jobs`.
4. `receipts`.
5. `ocr_results`.

## 9. Receipt Creation Logic

If email has image attachment:

1. Save attachment.
2. Create receipt.
3. Run OCR.
4. Store OCR text.
5. Use parsed total if found.

If email has PDF attachment and PDF support is not ready:

1. Create failed ingestion job.
2. Do not create confirmed receipt.
3. Show user that PDF support is not enabled yet.

If email has HTML or text receipt body:

1. Extract body text.
2. Parse merchant, total, date if possible.
3. Create receipt with source `gmail`.
4. Store raw body text in OCR result or equivalent extracted text table.
5. Set status `pending_review`.

## 10. Security Requirements

1. Use least privilege Gmail scopes.
2. Encrypt refresh tokens at rest.
3. Allow user to disconnect Gmail.
4. Delete encrypted token on disconnect.
5. Never expose one user's Gmail messages to another user.
6. Do not store full email contents unless needed for receipt review.
7. Store message ID for duplicate prevention.
8. Mark processed messages only after successful processing.

## 11. Future Push Notification Upgrade

Later version can use Gmail watch plus Google Cloud Pub/Sub. This would reduce polling but requires more cloud setup. The initial version should keep scheduled polling because it matches the daily receipt inbox requirement and is easier to self host.

## 12. Acceptance Criteria

1. User can connect Gmail.
2. User can set receipt label and daily time.
3. Worker imports receipts from that label.
4. Duplicate Gmail messages are skipped.
5. Successfully processed emails are marked or labeled as processed.
6. Failed emails appear in integration status or job history.
7. Disconnecting Gmail stops future ingestion.
8. Manual run now works.


<!-- 05_AUTH_STRIPE_PRD.md -->


# Authentication And Stripe Product Requirements Document

## 1. Purpose

Add accounts and subscription billing so Receipt Finance Tracker can support multiple users and paid signup.

## 2. Authentication Requirements

### Account Model

Users sign up with:

1. Username.
2. Password.
3. Email, optional for MVP but recommended for billing and password recovery.

### Login Model

1. Username or email plus password.
2. Session stored in secure HTTP only cookie.
3. Backend validates session on protected API requests.

### Password Rules

1. Minimum 12 characters recommended.
2. Store only password hash.
3. Use Argon2id or bcrypt.
4. Never log passwords.
5. Password reset can be a later version if email delivery is not ready.

## 3. Authorization Requirements

1. Users can only access their own receipts.
2. Users can only access their own integrations.
3. Users can only access their own billing portal session.
4. Admin routes require role `admin`.
5. Every receipt query must filter by user ID.

## 4. Session Requirements

1. Use HTTP only cookies.
2. Use secure cookies in production.
3. Session expiration required.
4. Logout clears cookie.
5. API returns 401 for unauthenticated requests.

## 5. Stripe Billing Requirements

### Plans

Recommended MVP plans:

1. Free
   1. 50 receipts per month.
   2. Web upload only.
   3. Basic dashboard.

2. Pro
   1. Higher receipt limit.
   2. Telegram ingestion.
   3. Gmail ingestion.
   4. CSV export.
   5. Advanced analytics.

### Stripe Flow

1. User opens billing page.
2. User clicks upgrade.
3. Backend creates Stripe Checkout Session.
4. User completes checkout on Stripe.
5. Stripe sends webhook to backend.
6. Backend creates or updates subscription row.
7. Front end shows active plan.

### Customer Portal Flow

1. Paid user clicks Manage billing.
2. Backend creates Stripe customer portal session.
3. User manages payment method or cancellation on Stripe.
4. Stripe webhook updates local subscription state.

## 6. Stripe Webhook Events

Handle these minimum events:

1. `checkout.session.completed`.
2. `customer.subscription.created`.
3. `customer.subscription.updated`.
4. `customer.subscription.deleted`.
5. `invoice.payment_succeeded`.
6. `invoice.payment_failed`.

## 7. Plan Enforcement

Backend should enforce limits, not just the front end.

Examples:

1. Free plan can upload only 50 receipts per month.
2. Free plan cannot enable Telegram.
3. Free plan cannot enable Gmail.
4. Disabled subscription cannot create new ingestion jobs.

## 8. API Endpoints

### POST `/auth/register`

Request:

```json
{
  "username": "grant",
  "email": "grant@example.com",
  "password": "long-password"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "username": "grant",
    "email": "grant@example.com"
  }
}
```

### POST `/auth/login`

Request:

```json
{
  "username": "grant",
  "password": "long-password"
}
```

Response:

```json
{
  "ok": true
}
```

### GET `/auth/me`

Response:

```json
{
  "id": "uuid",
  "username": "grant",
  "role": "user",
  "plan": "pro"
}
```

### POST `/billing/create-checkout-session`

Response:

```json
{
  "url": "https://checkout.stripe.com/..."
}
```

### POST `/billing/webhook`

Receives Stripe webhook body and validates signature.

## 9. Database Requirements

Use these tables:

1. `users`.
2. `subscriptions`.

Optional tables:

1. `sessions`.
2. `password_reset_tokens`.
3. `billing_events`.

## 10. Security Requirements

1. Verify Stripe webhook signature.
2. Store Stripe secret key only on server.
3. Never expose Stripe secret key to browser.
4. Never trust plan changes from front end.
5. Store password hash only.
6. Rate limit login attempts.
7. Use CSRF protection if needed based on session strategy.
8. Do not store card data.

## 11. Acceptance Criteria

1. User can register.
2. User can log in.
3. User can log out.
4. Protected pages redirect anonymous users.
5. Backend rejects unauthorized receipt access.
6. User can start Stripe Checkout.
7. Stripe webhook updates subscription status.
8. Billing page shows current plan.
9. Plan limits are enforced by backend.


<!-- 06_DEPLOYMENT_PRD.md -->


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

5. `telegram`
   1. Telegram bridge.
   2. Internal only.

6. `db`
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
8. Persist Telegram registration data.
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
3. Persistent Telegram mappings volume.
4. `.env` stored securely outside repo.

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
6. Telegram service status.
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
6. Telegram registration persists across restarts.
7. Restarting containers does not lose receipt data.
8. Backups can be created with one command.
9. Admin can see service health.


<!-- 07_CODEX_IMPLEMENTATION_PLAN.md -->


# Codex Implementation Plan

## 1. How To Use This File

Feed Codex one phase at a time. Do not ask Codex to build the entire app in one prompt. Each phase should produce a small working slice and tests where practical.

## 2. Phase 1 Backend Refactor And Database

Prompt:

```text
You are working in the Receipt Finance Tracker repository.

Refactor the backend into a clean FastAPI API service and a separate OCR service while preserving the existing imageContainer and informationHandler idea. Add PostgreSQL database support with migrations. Create tables for users, subscriptions, receipts, receipt_images, ocr_results, categories, integration_connections, telegram_mappings, gmail_connections, gmail_processed_messages, and ingestion_jobs.

The OCR service should accept an uploaded image and return raw OCR text plus parsed total. The API service should own all database writes and call the OCR service. Add health endpoints. Add environment variable configuration. Add tests for receipt upload parsing where practical.

Do not expose the OCR service publicly. Do not remove EasyOCR. Keep the current total extraction behavior as parser version easyocr_total_v1, but make it easier to improve later.
```

## 3. Phase 2 Authentication

Prompt:

```text
Add username and password authentication to the Receipt Finance Tracker API and front end. Use secure password hashing, HTTP only session cookies, and protected routes. Users must only access their own receipts and integrations.

Implement register, login, logout, and me endpoints. Add middleware or dependency based auth in FastAPI. Add login and register pages in Next.js. Add redirect behavior for protected pages. Add basic rate limiting to login if practical.
```

## 4. Phase 3 Front End Dashboard

Prompt:

```text
Build the main Next.js dashboard for Receipt Finance Tracker. Create app shell navigation, dashboard cards, upload page, receipts list page, receipt detail review page, analytics page, integrations page, billing page, and settings page.

Use the API client to fetch real backend data. Create reusable components for receipt upload, receipt table, receipt image preview, OCR raw text panel, category selector, status badges, and spending charts. The receipt detail page must allow correcting merchant, date, amount, category, and notes.
```

## 5. Phase 4 Web Receipt Upload

Prompt:

```text
Implement the complete web receipt upload flow. The user uploads JPG, PNG, or WebP. The API validates the file, stores it, creates a receipt with status processing, calls the OCR service, stores raw OCR output, stores parsed fields, and returns a receipt ID. The front end shows upload progress, processing state, and then routes to the receipt review page.

Add duplicate prevention using SHA256 where practical. Add structured error handling and user friendly messages.
```

## 6. Phase 5 Analytics

Prompt:

```text
Implement analytics endpoints and front end charts for Receipt Finance Tracker. Add summary totals, monthly spending, category breakdown, merchant breakdown, and source breakdown. Analytics should include only confirmed receipts by default, with an option to include pending review receipts.

Make sure totals match the filtered receipt list. Format amounts as currency. Handle empty states cleanly.
```

## 7. Phase 6 Telegram Integration

Prompt:

```text
Add Telegram bot ingestion using the official Telegram Bot API. Implement Telegram linking with a `/start CODE` verification flow. Add a webhook endpoint for incoming Telegram updates protected by Telegram secret header. When a linked Telegram sender sends an image attachment, create a receipt with source telegram, process it through OCR, store the result, and send a confirmation reply.

Prevent duplicates by Telegram update ID or attachment hash. Unknown senders should receive linking instructions.
```

## 8. Phase 7 Gmail Integration

Prompt:

```text
Add Gmail receipt ingestion. Implement Google OAuth connection, encrypted refresh token storage, Gmail label settings, daily scheduled ingestion, manual run now, and duplicate prevention by Gmail message ID.

The worker should search the configured Gmail label, download image attachments, parse HTML or text receipt bodies when no image exists, create receipts with source gmail, and mark or label processed messages. Failed messages should create ingestion job errors visible in the integrations page.
```

## 9. Phase 8 Stripe Billing

Prompt:

```text
Add Stripe subscription billing. Implement free and pro plans. Add backend endpoints to create Stripe Checkout Sessions and Stripe Customer Portal Sessions. Add webhook handling for checkout.session.completed, customer.subscription.created, customer.subscription.updated, customer.subscription.deleted, invoice.payment_succeeded, and invoice.payment_failed.

Store subscription state in PostgreSQL. Enforce plan limits in the backend. Do not trust front end plan state. Add billing page UI.
```

## 10. Phase 9 Production Deployment

Prompt:

```text
Create production Docker compose setup for Receipt Finance Tracker. Services should include web, api, ocr, worker, db, and nginx. Expose only nginx publicly. Add persistent volumes for PostgreSQL, receipt uploads, and Persistent Telegram mappings. Add Nginx HTTPS reverse proxy config, health checks, environment variable docs, backup scripts, and deployment instructions for a VPS.

Do not expose PostgreSQL or OCR directly to the internet.
```

## 11. Phase 10 Polish And Hardening

Prompt:

```text
Polish Receipt Finance Tracker for real users. Add loading states, empty states, better errors, mobile responsive receipt upload, admin health page, failed job retry, CSV export, category management, and tests for auth, receipt ownership, upload, Gmail duplicate prevention, and Stripe webhook signature verification.
```


<!-- 08_REPO_GAP_ANALYSIS.md -->


# Repository Gap Analysis

## 1. What Exists Now

The repo already has a strong prototype direction:

1. EasyOCR based receipt image processing.
2. FastAPI image upload endpoint.
3. Separate information handler service.
4. Dockerfiles for both Python services.
5. Docker compose with PostgreSQL.
6. Early PostgreSQL table idea.
7. README product vision for receipt uploads, finance tables, graphs, categories, and future email receipts.

## 2. Main Gaps

### 2.1 No Real Front End Yet

The README says Next.js front end, but the repo currently appears mostly backend focused. A complete Next.js app needs to be added.

### 2.2 No Multi User Auth Yet

The app needs user accounts before adding Telegram, Gmail, and Stripe because every receipt must belong to one user.

### 2.3 Database Schema Is Too Small

Current table idea only has:

1. ReceiptID.
2. Date.
3. Type of Expense.
4. Amount.

The production app needs users, receipts, images, OCR results, categories, integrations, jobs, Gmail processed messages, and subscriptions.

### 2.4 OCR Service Returns Too Little

Current OCR returns mainly a cost. It should return:

1. Raw OCR text.
2. Parsed total.
3. Parsed merchant if possible.
4. Parsed date if possible.
5. Parser version.
6. Confidence if available.

### 2.5 Temporary File Handling Needs Cleanup

Uploaded images are saved in containers. The production version should:

1. Store original uploads in persistent receipt storage.
2. Use temporary files only during processing.
3. Delete temporary files after processing.
4. Keep metadata in PostgreSQL.

### 2.6 No Background Job System Yet

Gmail scheduled ingestion and Telegram ingestion need a worker. The API request cycle should not handle every long running task directly.

### 2.7 No Integration Ownership Model Yet

Telegram numbers and Gmail accounts must map to users. This requires integration tables and strict ownership checks.

### 2.8 No Billing Yet

Stripe requires subscription state, webhook verification, plan enforcement, and a billing page.

### 2.9 Docker Compose Needs Production Hardening

Current compose exposes service ports directly. Production should expose only Nginx publicly, with internal networking for API, OCR, database, worker, and Telegram.

## 3. Biggest Technical Risk Areas

1. Telegram bot setup and webhook registration.
2. Gmail OAuth and refresh token security.
3. OCR reliability across receipt formats.
4. Duplicate prevention across web, Gmail, and Telegram.
5. User ownership and data isolation.
6. Stripe webhook correctness.
7. VPS storage and backups.

## 4. Recommended Next Commit

The best next commit should not be Telegram or Gmail yet. The best next commit is:

1. Add database migrations.
2. Add users table.
3. Add receipts and ocr_results tables.
4. Add auth.
5. Update upload flow to save a receipt under the authenticated user.

That gives every future feature a stable base.
