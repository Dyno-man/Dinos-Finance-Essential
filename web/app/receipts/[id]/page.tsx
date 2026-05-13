import { AppShell } from "@/components/AppShell";
import { OCRRawTextPanel } from "@/components/OCRRawTextPanel";
import { ReceiptImagePreview } from "@/components/ReceiptImagePreview";
import { ReceiptReviewForm } from "@/components/ReceiptReviewForm";
import { ReceiptStatusBadge } from "@/components/ReceiptStatusBadge";
import { formatCurrency, formatDate } from "@/lib/format";
import { getCategories, getReceiptDetail, requireUser } from "@/lib/server-api";

export default async function ReceiptDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const user = await requireUser();
  const { id } = await params;
  const [detail, categories] = await Promise.all([getReceiptDetail(id), getCategories()]);
  const receipt = detail.receipt;

  return (
    <AppShell user={user} title="Receipt review">
      <section className="detail-grid">
        <div>
          <ReceiptImagePreview receiptId={receipt.id} image={detail.images[0]} />
          <OCRRawTextPanel result={detail.ocr_result} />
        </div>
        <div className="panel-section">
          <div className="section-heading">
            <h2>{receipt.merchant_name ?? "Unknown merchant"}</h2>
            <ReceiptStatusBadge status={receipt.status} />
          </div>
          <dl className="metadata-list">
            <div>
              <dt>Amount</dt>
              <dd>{formatCurrency(receipt.amount_cents, receipt.currency)}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{formatDate(receipt.purchased_at)}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd className="capitalize">{receipt.source}</dd>
            </div>
          </dl>
          <ReceiptReviewForm receipt={receipt} categories={categories.categories} />
        </div>
      </section>
    </AppShell>
  );
}
