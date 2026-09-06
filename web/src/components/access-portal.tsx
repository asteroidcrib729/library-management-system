"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { useSession } from "@/components/session-provider";
import { apiRequest } from "@/lib/api/request";
import { ApiError, type Principal } from "@/lib/api/types";

type Mode = "bootstrap" | "login" | "register";

export function AccessPortal() {
  const router = useRouter();
  const session = useSession();
  const [mode, setMode] = useState<Mode>("login");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();

  useEffect(() => {
    if (session.phase === "signed-in") router.replace("/dashboard");
  }, [router, session.phase]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    setSuccess(undefined);
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") ?? "");
    const password = String(data.get("password") ?? "");
    try {
      if (mode === "login") {
        await session.login(username, password);
        router.replace("/dashboard");
        return;
      }
      const path =
        mode === "bootstrap"
          ? "/api/v1/accounts/bootstrap-administrator"
          : "/api/v1/accounts/register";
      await apiRequest<Principal>(path, {
        method: "POST",
        body: {
          display_name: String(data.get("displayName") ?? ""),
          username,
          password,
        },
      });
      setSuccess(
        mode === "bootstrap"
          ? "Administrator created. You can now sign in."
          : "Membership created. You can now sign in.",
      );
      setMode("login");
    } catch (reason) {
      setError(
        reason instanceof ApiError ? reason.message : "The request could not be completed.",
      );
    } finally {
      setPending(false);
    }
  }

  if (session.phase === "checking" || session.phase === "waking") {
    return (
      <div className="access-card" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        <div>
          <strong>
            {session.phase === "waking" ? "Waking the library service" : "Checking your session"}
          </strong>
          <p>Your sign-in screen will remain available if no session is found.</p>
        </div>
      </div>
    );
  }

  return (
    <section className="access-card" aria-labelledby="access-title">
      <div className="mode-tabs" role="tablist" aria-label="Account access">
        {(["login", "register", "bootstrap"] as const).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={mode === item}
            onClick={() => {
              setMode(item);
              setError(undefined);
              setSuccess(undefined);
            }}
          >
            {item === "login" ? "Sign in" : item === "register" ? "Join" : "First setup"}
          </button>
        ))}
      </div>
      <div>
        <p className="eyebrow">{mode === "bootstrap" ? "One-time setup" : "Library access"}</p>
        <h2 id="access-title">
          {mode === "login"
            ? "Welcome back"
            : mode === "register"
              ? "Create your membership"
              : "Create the first administrator"}
        </h2>
      </div>
      <form onSubmit={submit} aria-describedby="form-notice">
        {mode !== "login" ? (
          <label>
            Display name
            <input name="displayName" autoComplete="name" required maxLength={100} />
          </label>
        ) : null}
        <label>
          Username
          <input name="username" autoComplete="username" required minLength={3} maxLength={32} />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "login" ? 1 : 12}
            maxLength={128}
          />
        </label>
        <button className="button button-primary" disabled={pending}>
          {pending
            ? "Please wait…"
            : mode === "login"
              ? "Enter dashboard"
              : mode === "register"
                ? "Create membership"
                : "Create administrator"}
        </button>
        <div id="form-notice" aria-live="polite">
          {error ? <p className="notice notice-error">{error}</p> : null}
          {success ? <p className="notice notice-success">{success}</p> : null}
          {session.phase === "unavailable" ? (
            <div className="notice notice-error">
              <span>{session.error?.message ?? "The service is not available."}</span>
              <button type="button" onClick={session.refresh}>
                Check again
              </button>
            </div>
          ) : null}
        </div>
      </form>
    </section>
  );
}
