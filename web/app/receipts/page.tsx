import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { ReceiptTable } from "@/components/ReceiptTable";
import { getCategories, getReceipts, requireUser } from "@/lib/server-api";

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
  query.set("limit", "50");
  return `?${query.toString()}`;
}

export default async function ReceiptsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const user = await requireUser();
  const params = (await searchParams) ?? {};
  const [receipts, categories] = await Promise.all([getReceipts(buildQuery(params)), getCategories()]);

  return (
    <AppShell user={user} title="Receipts">
      <section className="panel-section">
        <form className="filter-grid">
          <label>
            Merchant
            <input name="merchant" defaultValue={valueOfParam(params.merchant) ?? ""} placeholder="Search merchant" />
          </label>
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
          <label>
            Status
            <select name="status" defaultValue={valueOfParam(params.status) ?? ""}>
              <option value="">All statuses</option>
              <option value="pending_review">Pending review</option>
              <option value="confirmed">Confirmed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <label>
            Min amount
            <input name="min_amount_cents" inputMode="numeric" defaultValue={valueOfParam(params.min_amount_cents) ?? ""} placeholder="Cents" />
          </label>
          <label>
            Max amount
            <input name="max_amount_cents" inputMode="numeric" defaultValue={valueOfParam(params.max_amount_cents) ?? ""} placeholder="Cents" />
          </label>
          <div className="filter-actions">
            <button type="submit">Apply</button>
            <Link className="button secondary" href="/receipts">
              Clear
            </Link>
          </div>
        </form>
      </section>
      <section className="panel-section">
        <div className="section-heading">
          <h2>{receipts.total} receipt records</h2>
          <Link className="button" href="/upload">
            Upload
          </Link>
        </div>
        <ReceiptTable receipts={receipts.receipts} />
      </section>
    </AppShell>
  );
}
