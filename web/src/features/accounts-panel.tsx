"use client";

import { type FormEvent } from "react";

import { CommandNotice } from "@/components/async-state";
import { useCommand } from "@/hooks/use-command";

export function AccountsPanel() {
  const command = useCommand();

  async function submit(event: FormEvent<HTMLFormElement>, action: "create" | "deactivate") {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await command.execute({
      method: "POST",
      path: action === "create" ? "/api/v1/accounts/librarians" : "/api/v1/accounts/deactivate",
      body:
        action === "create"
          ? {
              display_name: String(data.get("displayName")),
              username: String(data.get("username")),
              password: String(data.get("password")),
            }
          : { username: String(data.get("username")) },
      successMessage: action === "create" ? "Librarian account created." : "Account deactivated.",
      onSuccess: () => form.reset(),
    });
  }

  return (
    <div className="panel-stack">
      <header className="panel-heading"><div><p className="eyebrow">Administration</p><h2>Account controls</h2><p>Create staff access and deactivate accounts with an auditable server-side decision.</p></div></header>
      <CommandNotice state={command.state} retry={command.retry} />
      <div className="staff-grid">
        <form className="work-form" onSubmit={(event) => void submit(event, "create")}><h3>Create librarian</h3><label>Display name<input name="displayName" required maxLength={100} /></label><label>Username<input name="username" required minLength={3} maxLength={32} /></label><label>Temporary password<input name="password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /></label><button className="button button-primary">Create librarian</button></form>
        <form className="work-form danger-zone" onSubmit={(event) => { event.preventDefault(); if (window.confirm("Deactivate this account and revoke all of its active sessions?")) void submit(event, "deactivate"); }}><h3>Deactivate account</h3><p>This immediately revokes every active browser session for the account.</p><label>Username<input name="username" required minLength={3} maxLength={32} /></label><button className="button button-danger">Deactivate account</button></form>
      </div>
    </div>
  );
}
