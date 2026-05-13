import { formatCurrency, formatDate } from "@/lib/format";
import type { Receipt } from "@/lib/types";
import { ReceiptActions } from "./ReceiptActions";
import { ReceiptStatusBadge } from "./ReceiptStatusBadge";

export function ReceiptTable({ receipts }: { receipts: Receipt[] }) {
  if (receipts.length === 0) {
    return (
      <div className="empty-state">
        <h2>No receipts found</h2>
        <p>Upload a receipt or adjust the filters to see stored spending records.</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Merchant</th>
            <th>Amount</th>
            <th>Category</th>
            <th>Source</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {receipts.map((receipt) => (
            <tr key={receipt.id}>
              <td>{formatDate(receipt.purchased_at ?? receipt.created_at)}</td>
              <td>{receipt.merchant_name ?? "Unknown merchant"}</td>
              <td>{formatCurrency(receipt.amount_cents, receipt.currency)}</td>
              <td>{receipt.category?.name ?? "Uncategorized"}</td>
              <td className="capitalize">{receipt.source}</td>
              <td>
                <ReceiptStatusBadge status={receipt.status} />
              </td>
              <td>
                <ReceiptActions receiptId={receipt.id} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
