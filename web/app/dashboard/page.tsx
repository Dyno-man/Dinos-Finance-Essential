import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/LogoutButton";
import { getCurrentUser } from "@/lib/server-api";

export default async function DashboardPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main className="shell">
      <section className="dashboard">
        <div className="topbar">
          <div>
            <h1>Receipt Finance Tracker</h1>
            <p>Signed in as {user.username}</p>
          </div>
          <LogoutButton />
        </div>
        <div className="card-grid">
          <article className="card">
            <h2>Plan</h2>
            <p>{user.plan}</p>
          </article>
          <article className="card">
            <h2>Uploads</h2>
            <p>Receipt upload review will connect here in the dashboard phase.</p>
          </article>
          <article className="card">
            <h2>Integrations</h2>
            <p>Signal and Gmail connection status will appear here.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
