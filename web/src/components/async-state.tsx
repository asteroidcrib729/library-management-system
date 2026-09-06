import type { ReactNode } from "react";

import type { ApiError } from "@/lib/api/types";

export function LoadingState({ waking = false }: { waking?: boolean }) {
  return (
    <div className="state-card" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <div>
        <strong>{waking ? "Waking the library service" : "Loading library data"}</strong>
        <p>
          {waking
            ? "A free backend can take about a minute to wake. This request will retry safely."
            : "This should only take a moment."}
        </p>
      </div>
    </div>
  );
}

export function ErrorState({ error, retry }: { error: ApiError; retry: () => void }) {
  const title =
    error.kind === "database_unavailable"
      ? "The database is paused"
      : error.kind === "service_warming" || error.kind === "network"
        ? "The service is not ready"
        : "This view could not be loaded";
  return (
    <div className="state-card state-card-error" role="alert">
      <div>
        <strong>{title}</strong>
        <p>{error.message}</p>
        {error.requestId ? <small>Request {error.requestId}</small> : null}
      </div>
      <button className="button button-secondary" type="button" onClick={retry}>
        Try again
      </button>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="empty-state">{children}</p>;
}

export function CommandNotice({
  state,
  retry,
}: {
  state:
    | { phase: "idle" }
    | { phase: "pending" }
    | { phase: "success"; message: string }
    | { phase: "error"; error: ApiError; canRetry: boolean };
  retry: () => void;
}) {
  if (state.phase === "idle") return null;
  if (state.phase === "pending") {
    return (
      <p className="notice" role="status">
        Saving…
      </p>
    );
  }
  if (state.phase === "success") {
    return (
      <p className="notice notice-success" role="status">
        {state.message}
      </p>
    );
  }
  return (
    <div className="notice notice-error" role="alert">
      <span>{state.error.message}</span>
      {state.canRetry ? (
        <button type="button" onClick={retry}>
          Retry the same command
        </button>
      ) : null}
    </div>
  );
}
