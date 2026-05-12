# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

# Receipt Finance Tracker Master Product Requirements Document


## 1. Product Summary

Receipt Finance Tracker is a self hosted receipt ingestion and spending dashboard application. The current repository already has the core OCR direction in place: a FastAPI image processing container reads uploaded receipt images, extracts text through EasyOCR, finds a total value, and returns the detected cost. A second FastAPI information handler forwards uploaded images to the OCR service. PostgreSQL is already present in the Docker compose plan.

The finished product should become a full web app where users can create accounts, upload receipts, text receipts through a Signal bot, connect Gmail receipt folders, review extracted receipt data, correct OCR mistakes, and view spending analytics by date, merchant, category, and source.

## 2. Primary Goals

1. Preserve the current backend direction instead of replacing it.
2. Build a production ready web front end around the receipt tracker.
3. Add user accounts using username and password authentication.
4. Store receipts in a scalable multi user PostgreSQL schema.
5. Support multiple receipt sources:
   1. Web upload.
   2. Signal bot image upload.
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

A user wants to track spending by uploading physical receipts, forwarding email receipts, or texting receipt images to a Signal number. They want the least manual work possible, but they still need the ability to correct OCR mistakes.

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

### 6.2 Signal Receipt Upload

1. User signs in.
2. User opens integrations.
3. User links their Signal phone number.
4. User sends a receipt image to their assigned Signal bot number or linked Signal identity.
5. Signal listener receives the message and attachment.
6. Backend maps Signal sender to the correct app user.
7. Backend creates receipt record with source `signal`.
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
2. User chooses a paid plan.
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
11. Basic Signal ingestion.
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
7. Signal confirmation message.
8. Plan usage limits.

### Could Have

1. Line item extraction.
2. Budget alerts.
3. Browser notification when OCR is complete.
4. Team or household accounts.

## 8. Success Metrics

1. User can create account and upload a receipt in under 60 seconds.
2. At least 95 percent of supported image uploads create a receipt record.
3. OCR result appears within 15 seconds for normal receipt images.
4. User can correct any OCR field before it affects analytics.
5. Gmail ingestion can process a daily receipt label without duplicates.
6. Signal ingestion correctly maps messages to the right user.
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
9. Signal sender mapping.
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
7. Add Signal ingestion.
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
7. Gmail and Signal ingestion are idempotent and do not create duplicates.
8. Stripe subscription state is based on webhooks, not front end trust.
9. The app can be deployed with one documented Docker compose production command.
