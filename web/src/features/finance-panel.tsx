"use client";

import { type FormEvent } from "react";

import { CommandNotice, EmptyState, ErrorState, LoadingState } from "@/components/async-state";
import { useCommand } from "@/hooks/use-command";
import { useResource } from "@/hooks/use-resource";
import type { FineView, Principal } from "@/lib/api/types";

export function FinancePanel({ principal }: { principal: Principal }) {
  const fines = useResource<FineView[]>("/api/v1/finance/fines?limit=100");
  const command = useCommand();
  const isStaff = principal.role !== "member";

  async function assess(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await command.execute({
      method: "POST",
      path: "/api/v1/finance/fines",
      body: {
        username: String(data.get("username")),
        amount: String(data.get("amount")),
        reason: String(data.get("reason")),
      },
      successMessage: "Fine assessed.",
      onSuccess: () => {
        form.reset();
        fines.retry();
      },
    });
  }

  return (
    <div className="panel-stack">
      <header className="panel-heading">
        <div><p className="eyebrow">Finance</p><h2>Fine history</h2><p>See every charge and its settlement status.</p></div>
      </header>
      <CommandNotice state={command.state} retry={command.retry} />
      {fines.phase === "loading" || fines.phase === "waking" ? (
        <LoadingState waking={fines.phase === "waking"} />
      ) : fines.phase === "error" ? (
        <ErrorState error={fines.error} retry={fines.retry} />
      ) : fines.data.length === 0 ? (
        <EmptyState>No fines are recorded for this account.</EmptyState>
      ) : (
        <div className="card-grid compact-grid">
          {fines.data.map((item) => (
            <article className="metric-card" key={item.fine.id}>
              <div className="split-line"><span className={`badge ${item.fine.status === "outstanding" ? "badge-danger" : ""}`}>{item.fine.status}</span><strong>PKR {item.fine.amount}</strong></div>
              <h3>{item.fine.reason}</h3>
              <p>{item.username} · {formatDate(item.fine.assessed_at)}</p>
              {isStaff && item.fine.status === "outstanding" ? (
                <div className="inline-actions">
                  <button className="text-button" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/finance/fines/${item.fine.id}/payment`, body: {}, successMessage: "Payment recorded.", onSuccess: fines.retry })}>Record paid</button>
                  {principal.role === "administrator" ? <button className="text-button text-danger" type="button" onClick={() => { if (window.confirm("Waive this fine? This creates a permanent settlement record.")) void command.execute({ method: "POST", path: `/api/v1/finance/fines/${item.fine.id}/waiver`, body: { reason: "Administrator-approved waiver" }, successMessage: "Fine waived.", onSuccess: fines.retry }); }}>Waive</button> : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
      {isStaff ? (
        <details className="work-form"><summary>Assess a manual fine</summary><form onSubmit={assess}><div className="form-grid"><label>Member username<input name="username" required /></label><label>Amount (PKR)<input name="amount" type="number" min="0.01" step="0.01" required /></label></div><label>Reason<textarea name="reason" required maxLength={500} /></label><button className="button button-primary">Assess fine</button></form></details>
      ) : null}
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
