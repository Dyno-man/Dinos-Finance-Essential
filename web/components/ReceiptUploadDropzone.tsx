"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadReceipt } from "@/lib/client-api";

const allowedMimeTypes = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp", "image/pjpeg"]);
const maxBytes = 10 * 1024 * 1024;
type UploadState = "ready" | "uploading" | "processing" | "duplicate" | "failed";

function sniffImageMime(file: File): string | null {
  if (file.type && allowedMimeTypes.has(file.type)) {
    return file.type;
  }
  const lower = file.name.toLowerCase();
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  if (lower.endsWith(".png")) {
    return "image/png";
  }
  if (lower.endsWith(".webp")) {
    return "image/webp";
  }
  return null;
}

export function ReceiptUploadDropzone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState("Choose a JPG, PNG, or WebP receipt image.");
  const [uploadState, setUploadState] = useState<UploadState>("ready");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submitFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setError("");
    if (!sniffImageMime(file)) {
      setUploadState("failed");
      setError("Use a JPG, PNG, or WebP image.");
      return;
    }
    if (file.size > maxBytes) {
      setUploadState("failed");
      setError("Receipt images must be 10 MB or smaller.");
      return;
    }
    setBusy(true);
    setUploadState("uploading");
    setProgress(0);
    setStatus("Uploading receipt image...");
    try {
      const result = await uploadReceipt(file, (percent) => {
        setProgress(percent);
        if (percent >= 100) {
          setUploadState("processing");
          setStatus("Processing receipt with OCR...");
        } else {
          setStatus(`Uploading receipt image... ${percent}%`);
        }
      });
      if (result.duplicate) {
        setUploadState("duplicate");
        setStatus(result.message ?? "This receipt was already uploaded. Opening the existing receipt...");
      } else {
        setUploadState("processing");
        setStatus("OCR complete. Opening receipt review...");
      }
      router.push(`/receipts/${result.receipt_id}`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Upload failed");
      setUploadState("failed");
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
        accept="image/jpeg,image/jpg,image/png,image/webp,image/pjpeg,.jpg,.jpeg,.png,.webp"
        capture="environment"
        onChange={(event) => void submitFile(event.target.files?.[0])}
      />
      <strong>{busy ? "Processing receipt" : "Upload receipt"}</strong>
      <p>{status}</p>
      {uploadState === "uploading" || uploadState === "processing" ? (
        <div className="upload-progress" aria-label="Upload progress">
          <div className="upload-progress-track">
            <div
              className="upload-progress-fill"
              style={{ width: `${uploadState === "processing" ? 100 : progress}%` }}
            />
          </div>
          <span>{uploadState === "processing" ? "Processing" : `${progress}%`}</span>
        </div>
      ) : null}
      <button type="button" disabled={busy}>
        Select image
      </button>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
