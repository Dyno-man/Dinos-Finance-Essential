import { AppShell } from "@/components/AppShell";
import { BarChart } from "@/components/SpendingCharts";
import { StatCard } from "@/components/StatCard";
import { formatCurrency } from "@/lib/format";
import { getAnalytics, getCategories, requireUser } from "@/lib/server-api";

type SearchParams = Record<string, string | string[] | undefined>;

function valueOfParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function buildQuery(params: SearchParams) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const normalized = valueOfParam(value);
    if (normalized) {
      query.set(key, normalized);
    }
  }
  return query.toString() ? `?${query.toString()}` : "";
}

export default async function AnalyticsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const user = await requireUser();
  const params = (await searchParams) ?? {};
  const [analytics, categories] = await Promise.all([getAnalytics(buildQuery(params)), getCategories()]);
  return (
    <AppShell user={user} title="Analytics">
      <section className="panel-section">
        <form className="filter-grid">
          <label>
            Start date
            <input name="start_date" type="date" defaultValue={valueOfParam(params.start_date) ?? ""} />
          </label>
          <label>
            End date
            <input name="end_date" type="date" defaultValue={valueOfParam(params.end_date) ?? ""} />
          </label>
          <label>
            Category
            <select name="category_id" defaultValue={valueOfParam(params.category_id) ?? ""}>
              <option value="">All categories</option>
              {categories.categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source
            <select name="source" defaultValue={valueOfParam(params.source) ?? ""}>
              <option value="">All sources</option>
              <option value="web">Web</option>
              <option value="signal">Signal</option>
              <option value="gmail">Gmail</option>
              <option value="manual">Manual</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Apply</button>
          </div>
        </form>
      </section>
      <section className="stat-grid">
        <StatCard label="Confirmed spend" value={formatCurrency(analytics.total_cents)} />
        <StatCard label="Confirmed receipts" value={String(analytics.confirmed_receipt_count)} />
        <StatCard label="Average amount" value={formatCurrency(analytics.average_receipt_cents)} />
        <StatCard label="Pending review" value={String(analytics.pending_review_count)} />
      </section>
      <section className="content-grid">
        <BarChart title="Spending by month" rows={analytics.monthly_spend.map((row) => ({ label: row.month, value: row.amount_cents }))} />
        <BarChart
          title="Spending by category"
          rows={analytics.category_spend.map((row) => ({ label: row.name, value: row.amount_cents, color: row.color }))}
        />
        <BarChart title="Spending by merchant" rows={analytics.merchant_spend.map((row) => ({ label: row.merchant_name, value: row.amount_cents }))} />
        <section className="panel-section">
          <div className="section-heading">
            <h2>Receipts by source</h2>
          </div>
          {analytics.source_counts.length === 0 ? (
            <p className="muted">No confirmed receipt sources yet.</p>
          ) : (
            <div className="mini-grid">
              {analytics.source_counts.map((row) => (
                <article key={row.source}>
                  <strong className="capitalize">{row.source}</strong>
                  <p>{row.count} receipts</p>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    </AppShell>
  );
}
