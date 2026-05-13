import { AppShell } from "@/components/AppShell";
import { CategoryManager } from "@/components/CategoryManager";
import { getCategories, requireUser } from "@/lib/server-api";

export default async function SettingsPage() {
  const user = await requireUser();
  const categories = await getCategories();
  return (
    <AppShell user={user} title="Settings">
      <section className="content-grid">
        <section className="panel-section">
          <div className="section-heading">
            <h2>Profile</h2>
          </div>
          <dl className="metadata-list">
            <div>
              <dt>Username</dt>
              <dd>{user.username}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email ?? "Not set"}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{user.role}</dd>
            </div>
          </dl>
        </section>
        <section className="panel-section">
          <div className="section-heading">
            <h2>Account tools</h2>
          </div>
          <div className="button-row">
            <button type="button" disabled>
              Change password
            </button>
            <button type="button" className="secondary" disabled>
              Export CSV
            </button>
            <button type="button" className="danger-button" disabled>
              Delete account
            </button>
          </div>
        </section>
      </section>
      <CategoryManager categories={categories.categories} />
    </AppShell>
  );
}
