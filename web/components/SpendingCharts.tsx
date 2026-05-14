import { formatCurrency } from "@/lib/format";

export function BarChart({
  title,
  rows,
  emptyMessage = "No confirmed receipt data yet.",
}: {
  title: string;
  rows: { label: string; value: number; color?: string | null }[];
  emptyMessage?: string;
}) {
  const max = Math.max(...rows.map((row) => row.value), 0);
  return (
    <section className="panel-section">
      <div className="section-heading">
        <h2>{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="muted">{emptyMessage}</p>
      ) : (
        <div className="bar-list">
          {rows.map((row) => (
            <div className="bar-row" key={row.label}>
              <div className="bar-label">
                <span>{row.label}</span>
                <strong>{formatCurrency(row.value)}</strong>
              </div>
              <div className="bar-track" aria-hidden="true">
                <div
                  className="bar-fill"
                  style={{ width: `${max ? Math.max((row.value / max) * 100, 4) : 0}%`, background: row.color ?? undefined }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
