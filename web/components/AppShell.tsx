import Link from "next/link";
import type { ReactNode } from "react";
import type { AuthUser } from "@/lib/types";
import { LogoutButton } from "./LogoutButton";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/receipts", label: "Receipts" },
  { href: "/upload", label: "Upload" },
  { href: "/analytics", label: "Analytics" },
  { href: "/integrations", label: "Integrations" },
  { href: "/billing", label: "Billing" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ user, title, children }: { user: AuthUser; title: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">R</span>
          <span>Receipt Finance Tracker</span>
        </Link>
        <nav className="nav-list" aria-label="Main navigation">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="app-main">
        <header className="app-topbar">
          <div>
            <p className="eyebrow">Signed in as {user.username}</p>
            <h1>{title}</h1>
          </div>
          <LogoutButton />
        </header>
        {children}
      </div>
    </div>
  );
}
