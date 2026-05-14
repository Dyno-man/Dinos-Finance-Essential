"use client";

import { FormEvent, useState } from "react";
import { browserApi } from "@/lib/client-api";

export function TelegramLinkForm() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setLoading(true);

    try {
      const response = await browserApi("/integrations/telegram/link", {
        method: "POST",
        body: JSON.stringify({}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(body.error?.message ?? body.detail ?? "Could not start Telegram linking.");
        return;
      }
      setMessage(body.message ?? "Send the verification command to the Telegram bot.");
    } catch {
      setError("Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="inline-form telegram-link-form" onSubmit={onSubmit}>
      <button type="submit" disabled={loading}>
        {loading ? "Creating code..." : "Connect Telegram"}
      </button>
      <div className="form-message">
        {message ? <span className="success">{message}</span> : null}
        {error ? <span className="error">{error}</span> : null}
      </div>
    </form>
  );
}
