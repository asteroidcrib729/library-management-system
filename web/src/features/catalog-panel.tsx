"use client";

import { useState, type FormEvent } from "react";

import { CommandNotice, EmptyState, ErrorState, LoadingState } from "@/components/async-state";
import { useCommand } from "@/hooks/use-command";
import { useResource } from "@/hooks/use-resource";
import type { CatalogEntry, Principal, ReservationView } from "@/lib/api/types";

export function CatalogPanel({ principal }: { principal: Principal }) {
  const [query, setQuery] = useState("");
  const path = `/api/v1/catalog/books?limit=100${query ? `&query=${encodeURIComponent(query)}` : ""}`;
  const catalog = useResource<CatalogEntry[]>(path);
  const command = useCommand<ReservationView>();
  const addBook = useCommand();
  const inventory = useCommand();
  const isStaff = principal.role !== "member";

  async function createBook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await addBook.execute({
      method: "POST",
      path: "/api/v1/catalog/books",
      body: {
        title: String(data.get("title")),
        author: String(data.get("author")),
        publication_year: Number(data.get("year")),
        category: String(data.get("category")) || null,
      },
      successMessage: "Book added to the catalog.",
      onSuccess: () => {
        form.reset();
        catalog.retry();
      },
    });
  }

  async function updateInventory(
    event: FormEvent<HTMLFormElement>,
    action: "add-copy" | "update-status",
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const barcode = String(data.get("barcode"));
    await inventory.execute({
      method: action === "add-copy" ? "POST" : "PATCH",
      path:
        action === "add-copy"
          ? `/api/v1/catalog/books/${Number(data.get("bookId"))}/copies`
          : `/api/v1/catalog/copies/${encodeURIComponent(barcode)}`,
      body: action === "add-copy" ? { barcode } : { status: String(data.get("status")) },
      successMessage:
        action === "add-copy" ? "Physical copy added." : "Copy status updated.",
      onSuccess: () => {
        form.reset();
        catalog.retry();
      },
    });
  }

  return (
    <div className="panel-stack">
      <header className="panel-heading">
        <div>
          <p className="eyebrow">Catalog</p>
          <h2>Find your next book</h2>
          <p>Search titles and authors, then reserve an available physical collection.</p>
        </div>
        <label className="search-field">
          <span>Search catalog</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Title or author"
          />
        </label>
      </header>

      <CommandNotice state={command.state} retry={command.retry} />
      {catalog.phase === "loading" || catalog.phase === "waking" ? (
        <LoadingState waking={catalog.phase === "waking"} />
      ) : catalog.phase === "error" ? (
        <ErrorState error={catalog.error} retry={catalog.retry} />
      ) : catalog.data.length === 0 ? (
        <EmptyState>No books match this search yet.</EmptyState>
      ) : (
        <div className="card-grid">
          {catalog.data.map((entry) => (
            <article className="book-card" key={entry.book.id}>
              <div className="book-mark" aria-hidden="true">
                {entry.book.title.slice(0, 1).toUpperCase()}
              </div>
              <div className="book-card-body">
                <p className="meta">{entry.book.category ?? "Uncategorized"}</p>
                <h3>{entry.book.title}</h3>
                <p>by {entry.book.author}</p>
                <div className="availability">
                  <span className={entry.available_copies ? "dot dot-good" : "dot"} />
                  {entry.available_copies} of {entry.total_copies} available
                </div>
                <button
                  className="button button-secondary"
                  type="button"
                  disabled={entry.total_copies === 0 || command.state.phase === "pending"}
                  onClick={() =>
                    void command.execute({
                      method: "POST",
                      path: `/api/v1/circulation/reservations/books/${entry.book.id}`,
                      successMessage: `Reserved “${entry.book.title}”.`,
                    })
                  }
                >
                  Reserve
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {isStaff ? (
        <section className="panel-stack" aria-labelledby="inventory-heading">
          <div>
            <p className="eyebrow">Staff workspace</p>
            <h3 id="inventory-heading">Catalog inventory</h3>
          </div>
          <div className="staff-grid">
            <details className="work-form">
              <summary>Add a catalog title</summary>
              <form onSubmit={createBook}>
                <div className="form-grid">
                  <label>Title<input name="title" required maxLength={300} /></label>
                  <label>Author<input name="author" required maxLength={200} /></label>
                  <label>Publication year<input name="year" type="number" min={1} max={9999} required /></label>
                  <label>Category<input name="category" maxLength={100} /></label>
                </div>
                <button className="button button-primary" disabled={addBook.state.phase === "pending"}>Add title</button>
                <CommandNotice state={addBook.state} retry={addBook.retry} />
              </form>
            </details>
            <details className="work-form">
              <summary>Add a physical copy</summary>
              <form onSubmit={(event) => void updateInventory(event, "add-copy")}>
                <label>Catalog book ID<input name="bookId" type="number" min={1} required /></label>
                <label>Barcode<input name="barcode" required maxLength={100} /></label>
                <button className="button button-primary" disabled={inventory.state.phase === "pending"}>Add copy</button>
              </form>
            </details>
            <details className="work-form">
              <summary>Update copy status</summary>
              <form onSubmit={(event) => void updateInventory(event, "update-status")}>
                <label>Barcode<input name="barcode" required maxLength={100} /></label>
                <label>
                  New status
                  <select name="status" defaultValue="available">
                    <option value="available">Available</option>
                    <option value="lost">Lost</option>
                    <option value="damaged">Damaged</option>
                    <option value="withdrawn">Withdrawn</option>
                  </select>
                </label>
                <button className="button button-secondary" disabled={inventory.state.phase === "pending"}>Update status</button>
              </form>
            </details>
          </div>
          <CommandNotice state={inventory.state} retry={inventory.retry} />
        </section>
      ) : null}
    </div>
  );
}
