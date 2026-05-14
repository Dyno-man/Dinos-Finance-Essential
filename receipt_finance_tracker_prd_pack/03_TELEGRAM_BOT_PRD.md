# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

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

1. User sends unsupported content.
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
