"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { jsonApi } from "@/lib/client-api";

export function ReceiptActions({ receiptId }: { receiptId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function deleteReceipt() {
    if (!window.confirm("Delete this receipt?")) {
      return;
    }
    setBusy(true);
    try {
      await jsonApi(`/receipts/${receiptId}`, { method: "DELETE" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="table-actions">
      <Link className="text-link" href={`/receipts/${receiptId}`}>
        Review
      </Link>
      <button type="button" className="link-button" disabled={busy} onClick={() => void deleteReceipt()}>
        Delete
      </button>
    </div>
  );
}
