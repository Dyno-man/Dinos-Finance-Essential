import type { ReceiptStatus } from "@/lib/types";

const labels: Record<ReceiptStatus, string> = {
  processing: "Processing",
  pending_review: "Pending review",
  confirmed: "Confirmed",
  failed: "Failed",
};

export function ReceiptStatusBadge({ status }: { status: ReceiptStatus }) {
  return <span className={`status-badge status-${status}`}>{labels[status] ?? status}</span>;
}
