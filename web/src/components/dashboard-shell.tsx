"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/async-state";
import { useSession } from "@/components/session-provider";

const InsightsPanel = dynamic(() => import("@/features/insights-panel").then((module) => module.InsightsPanel));
const CatalogPanel = dynamic(() => import("@/features/catalog-panel").then((module) => module.CatalogPanel));
const CirculationPanel = dynamic(() => import("@/features/circulation-panel").then((module) => module.CirculationPanel));
const FinancePanel = dynamic(() => import("@/features/finance-panel").then((module) => module.FinancePanel));
const EngagementPanel = dynamic(() => import("@/features/engagement-panel").then((module) => module.EngagementPanel));
const AccountsPanel = dynamic(() => import("@/features/accounts-panel").then((module) => module.AccountsPanel));

type Section = "accounts" | "catalog" | "circulation" | "engagement" | "finance" | "overview";

export function DashboardShell() {
  const router = useRouter();
  const session = useSession();
  const [section, setSection] = useState<Section>("overview");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (session.phase === "signed-out") router.replace("/");
  }, [router, session.phase]);

  if (session.phase === "checking" || session.phase === "waking") return <main id="main-content" className="center-page"><LoadingState waking={session.phase === "waking"} /></main>;
  if (session.phase === "unavailable" && session.error) return <main id="main-content" className="center-page"><ErrorState error={session.error} retry={session.refresh} /></main>;
  if (!session.principal) return null;

  const navigation: { id: Section; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "catalog", label: "Catalog" },
    { id: "circulation", label: "Loans & reservations" },
    { id: "finance", label: "Fines" },
    { id: "engagement", label: "Requests & feedback" },
  ];
  if (session.principal.role === "administrator") navigation.push({ id: "accounts", label: "Accounts" });

  const content = {
    overview: <InsightsPanel principal={session.principal} />,
    catalog: <CatalogPanel principal={session.principal} />,
    circulation: <CirculationPanel principal={session.principal} />,
    finance: <FinancePanel principal={session.principal} />,
    engagement: <EngagementPanel principal={session.principal} />,
    accounts: <AccountsPanel />,
  }[section];

  return (
    <div className="dashboard">
      <header className="mobile-header"><Link className="brand" href="/">Shelfwise</Link><button className="button button-secondary" type="button" aria-expanded={menuOpen} aria-controls="dashboard-navigation" onClick={() => setMenuOpen((value) => !value)}>Menu</button></header>
      <aside className={menuOpen ? "sidebar sidebar-open" : "sidebar"} id="dashboard-navigation">
        <div><Link className="brand" href="/">Shelfwise<span>Library workspace</span></Link><nav aria-label="Dashboard sections">{navigation.map((item) => <button key={item.id} type="button" aria-current={section === item.id ? "page" : undefined} onClick={() => { setSection(item.id); setMenuOpen(false); }}>{item.label}</button>)}</nav></div>
        <div className="profile"><span className="avatar" aria-hidden="true">{session.principal.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{session.principal.display_name}</strong><small>{session.principal.role}</small></div><button className="text-button" type="button" onClick={() => void session.logout()}>Sign out</button></div>
      </aside>
      <main id="main-content" className="dashboard-main" tabIndex={-1}>{content}</main>
    </div>
  );
}
