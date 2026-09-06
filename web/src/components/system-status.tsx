"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";

type Status = "checking" | "available" | "unavailable";

const indicatorStyles: Record<Status, string> = {
  checking: "bg-amber-600 shadow-[0_0_0_4px_rgb(186_141_50_/_12%)]",
  available: "bg-accent shadow-[0_0_0_4px_rgb(21_163_139_/_12%)]",
  unavailable: "bg-danger shadow-[0_0_0_4px_rgb(186_73_61_/_12%)]",
};

export function SystemStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const { data, error } = await apiClient.GET("/health/live");
        if (active) {
          setStatus(!error && data?.status === "ok" ? "available" : "unavailable");
        }
      } catch {
        if (active) {
          setStatus("unavailable");
        }
      }
    };
    void check();
    return () => {
      active = false;
    };
  }, []);

  const label = {
    checking: "Checking local API",
    available: "Local API available",
    unavailable: "Local API is not running",
  }[status];

  return (
    <p
      className="m-0 inline-flex items-center gap-2.5 rounded-full border border-border bg-white/45 px-3.5 py-2 font-mono text-xs text-muted dark:bg-white/3"
      data-status={status}
      aria-live="polite"
    >
      <span
        className={`size-2 shrink-0 rounded-full ${indicatorStyles[status]}`}
        aria-hidden="true"
      />
      {label}
    </p>
  );
}
