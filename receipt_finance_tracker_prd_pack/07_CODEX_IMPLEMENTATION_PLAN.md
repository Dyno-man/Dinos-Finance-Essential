# Codex Implementation Plan

## 1. How To Use This File

Feed Codex one phase at a time. Do not ask Codex to build the entire app in one prompt. Each phase should produce a small working slice and tests where practical.

## 2. Phase 1 Backend Refactor And Database

Prompt:

```text
You are working in the Receipt Finance Tracker repository.

Refactor the backend into a clean FastAPI API service and a separate OCR service while preserving the existing imageContainer and informationHandler idea. Add PostgreSQL database support with migrations. Create tables for users, subscriptions, receipts, receipt_images, ocr_results, categories, integration_connections, signal_mappings, gmail_connections, gmail_processed_messages, and ingestion_jobs.

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

## 7. Phase 6 Signal Integration

Prompt:

```text
Add Signal bot ingestion using a self hosted Signal bridge service. Implement Signal linking by phone number and verification code. Add an internal endpoint or worker consumer for incoming Signal messages. When a linked Signal sender sends an image attachment, create a receipt with source signal, process it through OCR, store the result, and send a confirmation reply.

Prevent duplicates by Signal message ID or attachment hash. Unknown senders should receive linking instructions. Keep Signal endpoints internal or protected by a shared secret.
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
Create production Docker compose setup for Receipt Finance Tracker. Services should include web, api, ocr, worker, signal, db, and nginx. Expose only nginx publicly. Add persistent volumes for PostgreSQL, receipt uploads, and Signal data. Add Nginx HTTPS reverse proxy config, health checks, environment variable docs, backup scripts, and deployment instructions for a VPS.

Do not expose PostgreSQL or OCR directly to the internet.
```

## 11. Phase 10 Polish And Hardening

Prompt:

```text
Polish Receipt Finance Tracker for real users. Add loading states, empty states, better errors, mobile responsive receipt upload, admin health page, failed job retry, CSV export, category management, and tests for auth, receipt ownership, upload, Gmail duplicate prevention, and Stripe webhook signature verification.
```
