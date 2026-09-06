"use client";

import { type FormEvent } from "react";

import { CommandNotice, EmptyState, ErrorState, LoadingState } from "@/components/async-state";
import { useCommand } from "@/hooks/use-command";
import { useResource } from "@/hooks/use-resource";
import type { BookRequestView, FeedbackView, Principal } from "@/lib/api/types";

export function EngagementPanel({ principal }: { principal: Principal }) {
  const requests = useResource<BookRequestView[]>("/api/v1/engagement/book-requests?limit=100");
  const feedback = useResource<FeedbackView[]>("/api/v1/engagement/feedback?limit=100");
  const command = useCommand();
  const isStaff = principal.role !== "member";
  const refresh = () => {
    requests.retry();
    feedback.retry();
  };

  async function submit(event: FormEvent<HTMLFormElement>, type: "request" | "feedback") {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await command.execute({
      method: "POST",
      path: type === "request" ? "/api/v1/engagement/book-requests" : "/api/v1/engagement/feedback",
      body: type === "request"
        ? {
            title: String(data.get("title")),
            author: String(data.get("author")),
            publication_year: data.get("year") ? Number(data.get("year")) : null,
          }
        : { content: String(data.get("content")) },
      successMessage: type === "request" ? "Book request submitted." : "Feedback submitted.",
      onSuccess: () => {
        form.reset();
        refresh();
      },
    });
  }

  async function acquire(event: FormEvent<HTMLFormElement>, requestId: number) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await command.execute({
      method: "POST",
      path: `/api/v1/engagement/book-requests/${requestId}/acquire`,
      body: { book_id: Number(data.get("bookId")) },
      successMessage: "Acquisition linked to the catalog.",
      onSuccess: refresh,
    });
  }

  return (
    <div className="panel-stack">
      <header className="panel-heading">
        <div>
          <p className="eyebrow">Requests & feedback</p>
          <h2>Help shape the collection</h2>
          <p>Request books and keep a transparent record of responses.</p>
        </div>
      </header>
      <CommandNotice state={command.state} retry={command.retry} />
      <div className="staff-grid">
        <form className="work-form" onSubmit={(event) => void submit(event, "request")}>
          <h3>Request a book</h3>
          <label>Title<input name="title" required maxLength={300} /></label>
          <label>Author<input name="author" required maxLength={200} /></label>
          <label>Publication year (optional)<input name="year" type="number" min={1} max={9999} /></label>
          <button className="button button-primary">Submit request</button>
        </form>
        <form className="work-form" onSubmit={(event) => void submit(event, "feedback")}>
          <h3>Share feedback</h3>
          <label>Your message<textarea name="content" required maxLength={4000} /></label>
          <button className="button button-primary">Submit feedback</button>
        </form>
      </div>

      <section>
        <h3>Book requests</h3>
        {requests.phase === "loading" || requests.phase === "waking" ? (
          <LoadingState waking={requests.phase === "waking"} />
        ) : requests.phase === "error" ? (
          <ErrorState error={requests.error} retry={requests.retry} />
        ) : requests.data.length === 0 ? (
          <EmptyState>No book requests yet.</EmptyState>
        ) : (
          <ul className="record-list">
            {requests.data.map((item) => (
              <li key={item.request.id}>
                <div>
                  <strong>{item.request.title}</strong>
                  <span>{item.request.author} · {item.username} · {item.request.status}</span>
                  {item.request.review_note ? <small>{item.request.review_note}</small> : null}
                  {item.acquired_book_title ? <small>Catalog title: {item.acquired_book_title}</small> : null}
                </div>
                {isStaff && item.request.status === "pending" ? (
                  <div className="inline-actions">
                    <button className="text-button" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/engagement/book-requests/${item.request.id}/review`, body: { status: "approved" }, successMessage: "Request approved.", onSuccess: refresh })}>Approve</button>
                    <button className="text-button text-danger" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/engagement/book-requests/${item.request.id}/review`, body: { status: "rejected", note: "Not selected for the collection" }, successMessage: "Request rejected.", onSuccess: refresh })}>Reject</button>
                  </div>
                ) : isStaff && item.request.status === "approved" ? (
                  <form className="inline-actions" onSubmit={(event) => void acquire(event, item.request.id)}>
                    <label>Catalog book ID<input name="bookId" type="number" min={1} required /></label>
                    <button className="text-button" disabled={command.state.phase === "pending"}>Mark acquired</button>
                  </form>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3>Feedback</h3>
        {feedback.phase === "loading" || feedback.phase === "waking" ? (
          <LoadingState waking={feedback.phase === "waking"} />
        ) : feedback.phase === "error" ? (
          <ErrorState error={feedback.error} retry={feedback.retry} />
        ) : feedback.data.length === 0 ? (
          <EmptyState>No feedback yet.</EmptyState>
        ) : (
          <ul className="record-list">
            {feedback.data.map((item) => (
              <li key={item.feedback.id}>
                <div>
                  <strong>{item.username}</strong>
                  <span>{item.feedback.content}</span>
                  <small>{item.feedback.status}</small>
                </div>
                {isStaff && item.feedback.status !== "archived" ? (
                  <button className="text-button" type="button" onClick={() => void command.execute({ method: "POST", path: `/api/v1/engagement/feedback/${item.feedback.id}/${item.feedback.status === "new" ? "review" : "archive"}`, successMessage: item.feedback.status === "new" ? "Feedback reviewed." : "Feedback archived.", onSuccess: refresh })}>{item.feedback.status === "new" ? "Mark reviewed" : "Archive"}</button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
