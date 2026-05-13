import { AppShell } from "@/components/AppShell";
import { getBillingSummary, requireUser } from "@/lib/server-api";

export default async function BillingPage() {
  const user = await requireUser();
  const billing = await getBillingSummary();
  return (
    <AppShell user={user} title="Billing">
      <section className="panel-section billing-panel">
        <p className="eyebrow">Current plan</p>
        <h2>{billing.plan_name}</h2>
        <dl className="metadata-list">
          <div>
            <dt>Status</dt>
            <dd>{billing.status}</dd>
          </div>
          <div>
            <dt>Period end</dt>
            <dd>{billing.current_period_end ?? "Not set"}</dd>
          </div>
          <div>
            <dt>Canceling</dt>
            <dd>{billing.cancel_at_period_end ? "Yes" : "No"}</dd>
          </div>
        </dl>
        <div className="button-row">
          <button type="button" disabled>
            Upgrade
          </button>
          <button type="button" className="secondary" disabled>
            Manage billing
          </button>
        </div>
      </section>
    </AppShell>
  );
}
