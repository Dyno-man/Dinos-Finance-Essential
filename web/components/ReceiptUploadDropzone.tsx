"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadReceipt } from "@/lib/client-api";

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const maxBytes = 10 * 1024 * 1024;

export function ReceiptUploadDropzone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState("Choose a JPG, PNG, or WebP receipt image.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submitFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setError("");
    if (!allowedTypes.has(file.type)) {
      setError("Use a JPG, PNG, or WebP image.");
      return;
    }
    if (file.size > maxBytes) {
      setError("Receipt images must be 10 MB or smaller.");
      return;
    }
    setBusy(true);
    setStatus("Uploading and running OCR...");
    try {
      const result = await uploadReceipt(file);
      router.push(`/receipts/${result.receipt_id}`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Upload failed");
      setStatus("Choose another receipt image.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="upload-dropzone"
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          inputRef.current?.click();
        }
      }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        void submitFile(event.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={(event) => void submitFile(event.target.files?.[0])}
      />
      <strong>{busy ? "Processing receipt" : "Upload receipt"}</strong>
      <p>{status}</p>
      <button type="button" disabled={busy}>
        Select image
      </button>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
