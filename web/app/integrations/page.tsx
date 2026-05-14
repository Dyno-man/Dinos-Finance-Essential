import { AppShell } from "@/components/AppShell";
import { TelegramLinkForm } from "@/components/TelegramLinkForm";
import { getIntegrations, requireUser } from "@/lib/server-api";

const integrationCards = [
  { provider: "telegram", label: "Telegram", disconnectedText: "Telegram ingestion is not connected yet." },
  { provider: "gmail", label: "Gmail", disconnectedText: "Gmail ingestion is not connected yet." },
];

export default async function IntegrationsPage() {
  const user = await requireUser();
  const { integrations } = await getIntegrations();
  const byProvider = new Map(integrations.map((integration) => [integration.provider, integration]));

  return (
    <AppShell user={user} title="Integrations">
      <section className="content-grid">
        {integrationCards.map(({ provider, label, disconnectedText }) => {
          const integration = byProvider.get(provider);
          return (
            <article className="panel-section" key={provider}>
              <div className="section-heading">
                <h2>{label}</h2>
                <span className="status-badge">{integration?.status ?? "Not connected"}</span>
              </div>
              <p>{integration?.display_name ?? disconnectedText}</p>
              {provider === "telegram" ? (
                <TelegramLinkForm />
              ) : (
                <button type="button" disabled>
                  Connect {label}
                </button>
              )}
            </article>
          );
        })}
        <article className="panel-section">
          <div className="section-heading">
            <h2>Banking API</h2>
            <span className="status-badge">Future</span>
          </div>
          <p>Bank account ingestion is reserved for a later integration.</p>
          <button type="button" disabled>
            Unavailable
          </button>
        </article>
      </section>
    </AppShell>
  );
}
