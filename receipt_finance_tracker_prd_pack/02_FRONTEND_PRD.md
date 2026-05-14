# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

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

1. Paid users can open Stripe customer portal.
2. Subscription status updates after webhook sync.

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
