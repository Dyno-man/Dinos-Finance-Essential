import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { BarChart } from "@/components/SpendingCharts";
import { StatCard } from "@/components/StatCard";
import { ReceiptTable } from "@/components/ReceiptTable";
import { formatCurrency } from "@/lib/format";
import { getAnalytics, getIntegrations, getReceipts, requireUser } from "@/lib/server-api";

export default async function DashboardPage() {
  const user = await requireUser();
  const [analytics, receipts, integrations] = await Promise.all([
    getAnalytics(),
    getReceipts("?limit=5"),
    getIntegrations(),
  ]);

  return (
    <AppShell user={user} title="Dashboard">
      <section className="stat-grid">
        <StatCard label="Confirmed spend" value={formatCurrency(analytics.total_cents)} detail="From confirmed receipts" />
        <StatCard label="Receipts" value={String(analytics.receipt_count)} detail="Stored records" />
        <StatCard label="Average receipt" value={formatCurrency(analytics.average_receipt_cents)} detail="Confirmed receipts" />
        <StatCard label="Pending review" value={String(analytics.pending_review_count)} detail="Need correction or confirmation" />
      </section>
      <section className="content-grid">
        <BarChart
          title="Monthly spend"
          rows={analytics.monthly_spend.map((row) => ({ label: row.month, value: row.amount_cents }))}
        />
        <BarChart
          title="Category breakdown"
          rows={analytics.category_spend.map((row) => ({ label: row.name, value: row.amount_cents, color: row.color }))}
        />
      </section>
      <section className="panel-section">
        <div className="section-heading">
          <h2>Recent receipts</h2>
          <Link className="text-link" href="/receipts">
            View all
          </Link>
        </div>
        <ReceiptTable receipts={receipts.receipts} />
      </section>
      <section className="panel-section">
        <div className="section-heading">
          <h2>Ingestion status</h2>
          <Link className="text-link" href="/integrations">
            Manage
          </Link>
        </div>
        <div className="mini-grid">
          <article>
            <strong>Web uploads</strong>
            <p>Ready for manual receipt images.</p>
          </article>
          <article>
            <strong>Connected integrations</strong>
            <p>{integrations.integrations.length} active or pending connection records.</p>
          </article>
        </div>
      </section>
    </AppShell>
  );
}
