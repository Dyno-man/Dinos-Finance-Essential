# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

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
   3. Handles Signal message ingestion if not event driven.
   4. Handles OCR retry jobs.
   5. Can be built as a separate FastAPI worker process or a Python script container.

5. `signal`
   1. Signal bridge using signal cli rest api or similar.
   2. Receives and sends Signal messages.
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
5. plan_name text not null default `basic`.
6. status text not null default `basic`.
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

1. source must be one of `web`, `signal`, `gmail`, `manual`.
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

1. `signal`.
2. `gmail`.

### 4.8 signal_mappings

Purpose: map Signal sender phone numbers to app users.

Fields:

1. id UUID primary key.
2. user_id UUID references users not null.
3. signal_number text not null unique.
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
2. POST `/integrations/signal/link`.
3. DELETE `/integrations/signal`.
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
9. Signal webhook endpoints must reject unauthorized internal requests.
10. API should apply request rate limits to auth and upload endpoints.

## 10. Acceptance Criteria

1. A receipt uploaded through the web creates exactly one receipt row.
2. OCR raw text is always stored.
3. The app never trusts the OCR result as final until user review.
4. A failed OCR job marks receipt as `failed` and shows an error.
5. Retrying a failed job does not create duplicate receipts.
6. Gmail message IDs cannot be processed twice for the same user.
7. Signal sender phone number maps to exactly one user.
8. Deleting a user disables login and prevents new ingestion.
