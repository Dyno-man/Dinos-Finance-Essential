"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { CategorySelector } from "@/components/CategorySelector";
import { jsonApi } from "@/lib/client-api";
import { centsToInput, inputToCents } from "@/lib/format";
import type { Category, Receipt } from "@/lib/types";

function dateInputValue(value: string | null) {
  if (!value) {
    return "";
  }
  return new Date(value).toISOString().slice(0, 10);
}

export function ReceiptReviewForm({ receipt, categories }: { receipt: Receipt; categories: Category[] }) {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(formData: FormData, status?: string) {
    setBusy(true);
    setError("");
    setMessage("");
    const amount = inputToCents(String(formData.get("amount") ?? ""));
    try {
      await jsonApi(`/receipts/${receipt.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          merchant_name: String(formData.get("merchant_name") ?? "") || null,
          purchased_at: formData.get("purchased_at") ? `${formData.get("purchased_at")}T00:00:00Z` : null,
          amount_cents: amount,
          category_id: String(formData.get("category_id") ?? "") || null,
          notes: String(formData.get("notes") ?? "") || null,
          status,
        }),
      });
      setMessage(status === "confirmed" ? "Receipt confirmed." : "Receipt saved.");
      router.refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save(new FormData(event.currentTarget));
  }

  return (
    <form className="review-form" onSubmit={(event) => void onSubmit(event)}>
      <label>
        Merchant
        <input name="merchant_name" defaultValue={receipt.merchant_name ?? ""} />
      </label>
      <label>
        Purchase date
        <input name="purchased_at" type="date" defaultValue={dateInputValue(receipt.purchased_at)} />
      </label>
      <label>
        Amount
        <input name="amount" inputMode="decimal" defaultValue={centsToInput(receipt.amount_cents)} />
      </label>
      <label>
        Category
        <CategorySelector categories={categories} value={receipt.category_id} />
      </label>
      <label>
        Notes
        <textarea name="notes" defaultValue={receipt.notes ?? ""} />
      </label>
      <div className="button-row">
        <button type="submit" disabled={busy}>
          Save changes
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={(event) => void save(new FormData(event.currentTarget.form as HTMLFormElement), "confirmed")}
        >
          Save and confirm
        </button>
      </div>
      {message ? <p className="success">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </form>
  );
}
