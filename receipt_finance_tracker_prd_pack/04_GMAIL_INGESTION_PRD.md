# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

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

1. Runs every 60 minutes to check due Gmail ingestion schedules.
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
