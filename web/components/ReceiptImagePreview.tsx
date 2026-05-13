"use client";

import { publicApiUrl } from "@/lib/client-api";
import type { ReceiptImage } from "@/lib/types";

export function ReceiptImagePreview({ receiptId, image }: { receiptId: string; image?: ReceiptImage }) {
  if (!image) {
    return (
      <div className="image-preview empty-state">
        <p>No receipt image is stored for this record.</p>
      </div>
    );
  }
  return (
    <div className="image-preview">
      <img src={publicApiUrl(`/receipts/${receiptId}/image`)} alt={image.original_filename ?? "Uploaded receipt"} />
    </div>
  );
}
