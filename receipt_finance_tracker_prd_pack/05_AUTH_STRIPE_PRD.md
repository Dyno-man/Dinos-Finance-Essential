# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

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

1. Basic
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

1. Disabled subscription cannot create new ingestion jobs.

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
