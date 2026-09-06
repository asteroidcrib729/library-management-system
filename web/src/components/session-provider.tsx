"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiRequest } from "@/lib/api/request";
import { ApiError, type Principal, type Session } from "@/lib/api/types";

type SessionPhase = "checking" | "signed-in" | "signed-out" | "unavailable" | "waking";

interface SessionContextValue {
  error?: ApiError;
  phase: SessionPhase;
  principal?: Principal;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<SessionPhase>("checking");
  const [principal, setPrincipal] = useState<Principal>();
  const [error, setError] = useState<ApiError>();
  const [revision, setRevision] = useState(0);

  const clear = useCallback(() => {
    setPrincipal(undefined);
    setError(undefined);
    setPhase("signed-out");
  }, []);

  useEffect(() => {
    const unauthorized = () => clear();
    window.addEventListener("lms:unauthorized", unauthorized);
    return () => window.removeEventListener("lms:unauthorized", unauthorized);
  }, [clear]);

  useEffect(() => {
    const controller = new AbortController();
    async function restoreSession() {
      try {
        const session = await apiRequest<Session>("/api/v1/auth/session", {
          signal: controller.signal,
          onWarming: () => setPhase("waking"),
        });
        setPrincipal(session.principal);
        setError(undefined);
        setPhase("signed-in");
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        if (reason instanceof ApiError && reason.kind === "authentication") {
          clear();
          return;
        }
        setPrincipal(undefined);
        setError(
          reason instanceof ApiError
            ? reason
            : new ApiError("The service is unavailable.", "network"),
        );
        setPhase("unavailable");
      }
    }
    void restoreSession();
    return () => controller.abort();
  }, [clear, revision]);

  const login = useCallback(async (username: string, password: string) => {
    const session = await apiRequest<Session>("/api/v1/auth/login", {
      method: "POST",
      body: { username, password },
    });
    setPrincipal(session.principal);
    setError(undefined);
    setPhase("signed-in");
  }, []);

  const logout = useCallback(async () => {
    await apiRequest<void>("/api/v1/auth/logout", { method: "POST" });
    clear();
  }, [clear]);

  const refresh = useCallback(() => {
    setPhase("checking");
    setRevision((value) => value + 1);
  }, []);

  const value = useMemo(
    () => ({ error, login, logout, phase, principal, refresh }),
    [error, login, logout, phase, principal, refresh],
  );
  return <SessionContext value={value}>{children}</SessionContext>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider.");
  return context;
}
