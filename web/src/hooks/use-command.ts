"use client";

import { useCallback, useRef, useState } from "react";

import { apiRequest, createIdempotencyKey } from "@/lib/api/request";
import { ApiError } from "@/lib/api/types";

type CommandState =
  | { phase: "idle" }
  | { phase: "pending" }
  | { phase: "success"; message: string }
  | { phase: "error"; error: ApiError; canRetry: boolean };

interface PendingCommand<T> {
  body?: unknown;
  key: string;
  path: string;
  method: "DELETE" | "PATCH" | "POST" | "PUT";
  onSuccess?: (result: T) => void;
  successMessage: string;
}

export function useCommand<T = unknown>() {
  const [state, setState] = useState<CommandState>({ phase: "idle" });
  const pending = useRef<PendingCommand<T> | null>(null);

  const run = useCallback(async (command: PendingCommand<T>) => {
    setState({ phase: "pending" });
    try {
      const result = await apiRequest<T>(command.path, {
        body: command.body,
        idempotencyKey: command.key,
        method: command.method,
      });
      command.onSuccess?.(result);
      pending.current = null;
      setState({ phase: "success", message: command.successMessage });
    } catch (reason) {
      const error =
        reason instanceof ApiError
          ? reason
          : new ApiError("The request failed.", "unexpected");
      setState({
        phase: "error",
        error,
        canRetry: error.kind === "network" || error.kind === "service_warming",
      });
    }
  }, []);

  const execute = useCallback(
    async (command: Omit<PendingCommand<T>, "key">) => {
      const retained = { ...command, key: createIdempotencyKey() };
      pending.current = retained;
      await run(retained);
    },
    [run],
  );

  const retry = useCallback(async () => {
    if (pending.current) await run(pending.current);
  }, [run]);

  const reset = useCallback(() => {
    pending.current = null;
    setState({ phase: "idle" });
  }, []);

  return { execute, reset, retry, state };
}
