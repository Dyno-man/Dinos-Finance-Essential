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
