"use client";

import { type FormEvent } from "react";

import { CommandNotice, EmptyState, ErrorState, LoadingState } from "@/components/async-state";
import { useCommand } from "@/hooks/use-command";
import { useResource } from "@/hooks/use-resource";
import type { LoanView, Principal, ReservationView } from "@/lib/api/types";

export function CirculationPanel({ principal }: { principal: Principal }) {
  const loans = useResource<LoanView[]>("/api/v1/circulation/loans?limit=100");
  const reservations = useResource<ReservationView[]>(
    "/api/v1/circulation/reservations?limit=100",
  );
  const command = useCommand();
  const isStaff = principal.role !== "member";
  const refresh = () => {
    loans.retry();
    reservations.retry();
  };

  async function staffAction(event: FormEvent<HTMLFormElement>, action: "checkout" | "return") {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await command.execute({
      method: "POST",
      path:
        action === "checkout"
          ? "/api/v1/circulation/loans/checkout"
          : "/api/v1/circulation/loans/return",
      body:
        action === "checkout"
          ? {
              borrower_username: String(data.get("username")),
              barcode: String(data.get("barcode")),
            }
          : { barcode: String(data.get("barcode")) },
      successMessage: action === "checkout" ? "Copy checked out." : "Copy returned.",
      onSuccess: () => {
        form.reset();
        refresh();
      },
    });
  }

  return (
    <div className="panel-stack">
      <header className="panel-heading">
        <div>
          <p className="eyebrow">Circulation</p>
          <h2>Loans and reservations</h2>
          <p>Keep due dates and reservation queues visible.</p>
        </div>
      </header>
      <CommandNotice state={command.state} retry={command.retry} />
      <section aria-labelledby="loans-title">
        <h3 id="loans-title">Loans</h3>
        {loans.phase === "loading" || loans.phase === "waking" ? (
          <LoadingState waking={loans.phase === "waking"} />
        ) : loans.phase === "error" ? (
          <ErrorState error={loans.error} retry={loans.retry} />
        ) : loans.data.length === 0 ? (
          <EmptyState>No loans are recorded for this view.</EmptyState>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Book</th>
                  <th>Copy</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {loans.data.map((item) => (
                  <tr key={item.loan.id}>
                    <td><strong>{item.book.title}</strong><small>{item.borrower_username}</small></td>
                    <td><code>{item.copy.barcode}</code></td>
                    <td>{formatDate(item.loan.due_at)}</td>
                    <td><span className={`badge ${item.is_overdue ? "badge-danger" : ""}`}>{item.loan.returned_at ? "Returned" : item.is_overdue ? "Overdue" : "Active"}</span></td>
                    <td>
                      {!item.loan.returned_at ? (
                        <button className="text-button" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/circulation/loans/${item.loan.id}/renew`, successMessage: "Loan renewed.", onSuccess: refresh })}>Renew</button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section aria-labelledby="reservations-title">
        <h3 id="reservations-title">Reservations</h3>
        {reservations.phase === "loading" || reservations.phase === "waking" ? (
          <LoadingState waking={reservations.phase === "waking"} />
        ) : reservations.phase === "error" ? (
          <ErrorState error={reservations.error} retry={reservations.retry} />
        ) : reservations.data.length === 0 ? (
          <EmptyState>No reservations are waiting.</EmptyState>
        ) : (
          <ul className="record-list">
            {reservations.data.map((item) => (
              <li key={item.reservation.id}>
                <div><strong>{item.book_title}</strong><span>{item.reservation.status}{item.queue_position ? ` · Queue ${item.queue_position}` : ""}</span></div>
                {item.reservation.status === "active" ? <button className="text-button" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/circulation/reservations/${item.reservation.id}/cancel`, successMessage: "Reservation cancelled.", onSuccess: refresh })}>Cancel</button> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      {isStaff ? (
        <div className="staff-grid">
          <form className="work-form" onSubmit={(event) => void staffAction(event, "checkout")}>
            <h3>Check out a copy</h3>
            <label>Borrower username<input name="username" required /></label>
            <label>Barcode<input name="barcode" required /></label>
            <button className="button button-primary">Check out</button>
          </form>
          <form className="work-form" onSubmit={(event) => void staffAction(event, "return")}>
            <h3>Return a copy</h3>
            <label>Barcode<input name="barcode" required /></label>
            <button className="button button-primary">Record return</button>
          </form>
        </div>
      ) : null}
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
