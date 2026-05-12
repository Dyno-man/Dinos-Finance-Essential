# RULES TO FOLLOW AT ALL TIMES NO EXCEPTIONS ALLOWED
- You must make surgical edits minimum changes or code edits required for all processes
- We are building for longevity, this is not a one and done deal we want to build so those who come after have an easy time
- Do not take shortcuts or make hacky solutions to the problems, solve them gracefully and elegantly
- Reduce tech debt, this is a functioning app DO NOT let waste accumulate in our code

# Signal Bot Integration Product Requirements Document

## 1. Purpose

Allow each user to text receipt images directly to the app through Signal. The app should process the image with the existing OCR pipeline, save the receipt under the correct user, and optionally send a confirmation message back through Signal.

## 2. Integration Approach

Use a self hosted Signal bridge container such as `signal-cli-rest-api` so the VPS can receive Signal messages and attachments through an internal HTTP API. The app should not attempt to implement the Signal protocol itself.

Recommended design:

1. Run Signal bridge as its own Docker service.
2. Register or link a Signal number controlled by the app owner.
3. Use the bridge to receive messages and attachments.
4. Map sender phone numbers to app users.
5. Process incoming image attachments as receipt uploads.
6. Send confirmation messages back to the sender.

## 3. User Flow

### 3.1 Link Signal Number

1. User signs in.
2. User opens Integrations.
3. User selects Connect Signal.
4. App asks for the user's Signal phone number.
5. App generates a verification code.
6. User sends the code to the app Signal bot.
7. Signal listener receives the message.
8. App verifies the code.
9. App stores the sender number as linked.

### 3.2 Upload Receipt Through Signal

1. User sends receipt image to app Signal number.
2. Signal bridge receives message.
3. Worker downloads attachment.
4. Backend creates receipt with source `signal`.
5. OCR service extracts raw text and total.
6. Backend stores OCR result.
7. Backend sends reply:
   `Receipt received. I found $12.34. Review it here: <link>`

### 3.3 Failure Flow

1. User sends unsupported file.
2. App responds:
   `I could not process that file. Please send a JPG, PNG, or WebP receipt image.`
3. Failure is logged in ingestion jobs.

## 4. Requirements

### Must Have

1. Signal connection status on integrations page.
2. User phone number verification.
3. Incoming image attachment support.
4. Mapping from Signal sender to user.
5. Receipt creation with source `signal`.
6. OCR processing through existing OCR service.
7. Duplicate prevention based on Signal message ID or attachment hash.
8. Confirmation reply after successful receipt creation.
9. Friendly error reply after failure.

### Should Have

1. Support multiple images in one message.
2. Support text like `category grocery`.
3. Allow user to text `help`.
4. Allow user to text `unlink`.
5. Admin page for Signal service health.

### Could Have

1. Natural language corrections by text.
2. Monthly spending summaries over Signal.
3. Budget alerts over Signal.

## 5. Backend Endpoints

### POST `/integrations/signal/link`

Request:

```json
{
  "signal_number": "+15551234567"
}
```

Response:

```json
{
  "status": "pending_verification",
  "message": "Send code 123456 to the Signal bot."
}
```

### POST `/internal/signal/message`

Internal endpoint called by the Signal listener or worker.

Request:

```json
{
  "message_id": "signal_message_id",
  "sender_number": "+15551234567",
  "received_at": "2026-05-12T12:00:00Z",
  "text": "optional text",
  "attachments": [
    {
      "attachment_id": "abc",
      "filename": "receipt.jpg",
      "mime_type": "image/jpeg",
      "storage_path": "/tmp/signal/receipt.jpg"
    }
  ]
}
```

Response:

```json
{
  "status": "accepted",
  "created_receipts": ["receipt_uuid"]
}
```

## 6. Database Additions

Use the `signal_mappings` table from the architecture PRD.

Add optional table `signal_messages`:

1. id UUID primary key.
2. user_id UUID references users nullable.
3. sender_number text not null.
4. signal_message_id text not null unique.
5. raw_payload jsonb not null.
6. processed_at timestamptz nullable.
7. status text not null.
8. error_message text nullable.
9. created_at timestamptz not null.

## 7. Security Requirements

1. Internal Signal endpoint must not be public.
2. Use Docker internal network or shared secret header.
3. Never log full message attachment contents.
4. Never expose linked phone numbers to other users.
5. Store only needed Signal metadata.
6. Allow user to unlink Signal.
7. Rate limit messages per sender.
8. Validate file type and size before OCR.

## 8. Docker Compose Requirements

Add service:

```yaml
signal:
  image: bbernhard/signal-cli-rest-api:latest
  restart: unless-stopped
  volumes:
    - signal-data:/home/.local/share/signal-cli
  environment:
    - MODE=json-rpc
  networks:
    - internal
```

Exact configuration may change based on chosen Signal bridge mode.

## 9. Acceptance Criteria

1. User can link a Signal number.
2. User can send a receipt image by Signal.
3. App creates a receipt owned by that user.
4. Receipt source is `signal`.
5. OCR result is stored.
6. User receives a confirmation message.
7. Duplicate Signal messages do not create duplicate receipts.
8. Unknown senders receive a linking instruction.
9. Signal service restart does not erase registration data.
