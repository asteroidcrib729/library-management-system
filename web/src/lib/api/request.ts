import { getCsrfCookieName, getPublicApiBaseUrl } from "./config";
import { ApiError, type ApiErrorKind } from "./types";

type Method = "DELETE" | "GET" | "PATCH" | "POST" | "PUT";

export interface ApiRequestOptions {
  body?: unknown;
  idempotencyKey?: string;
  method?: Method;
  onWarming?: () => void;
  signal?: AbortSignal;
}

interface ErrorPayload {
  code?: string;
  message?: string;
  request_id?: string;
}

const sharedReads = new Map<string, Promise<unknown>>();
const retryDelays = [0, 800, 2_000, 4_000] as const;
const attemptTimeout = 20_000;

export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const key = method === "GET" ? `${method}:${path}` : undefined;
  if (key) {
    const existing = sharedReads.get(key);
    if (existing) return existing as Promise<T>;
  }
  const request = requestWithPolicy<T>(path, { ...options, method });
  if (key) {
    sharedReads.set(key, request);
    void request.then(
      () => sharedReads.delete(key),
      () => sharedReads.delete(key),
    );
  }
  return request;
}

async function requestWithPolicy<T>(
  path: string,
  options: ApiRequestOptions & { method: Method },
): Promise<T> {
  const attempts = options.method === "GET" ? retryDelays.length : 1;
  let lastError: ApiError | undefined;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) {
      options.onWarming?.();
      await delay(retryDelays[attempt], options.signal);
    }
    try {
      return await fetchOnce<T>(path, options);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") throw reason;
      const error = normalizeError(reason);
      lastError = error;
      const retryable =
        options.method === "GET" &&
        (error.kind === "network" || error.kind === "service_warming");
      if (!retryable || attempt === attempts - 1) throw error;
    }
  }
  throw lastError ?? new ApiError("The request failed.", "unexpected");
}

async function fetchOnce<T>(
  path: string,
  options: ApiRequestOptions & { method: Method },
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort("timeout"), attemptTimeout);
  const abort = () => controller.abort(options.signal?.reason);
  options.signal?.addEventListener("abort", abort, { once: true });
  const headers = new Headers({ Accept: "application/json" });
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.method !== "GET") {
    const csrf = readCookie(getCsrfCookieName());
    if (csrf) headers.set("X-CSRF-Token", csrf);
    if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
  }
  try {
    const response = await fetch(`${getPublicApiBaseUrl()}${path}`, {
      method: options.method,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "include",
      headers,
      signal: controller.signal,
    });
    if (!response.ok) throw await responseError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (reason) {
    if (reason instanceof ApiError) throw reason;
    if (options.signal?.aborted) throw new DOMException("Request cancelled", "AbortError");
    throw new ApiError(
      "The service could not be reached. It may still be waking up.",
      "network",
    );
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abort);
  }
}

async function responseError(response: Response): Promise<ApiError> {
  let payload: ErrorPayload = {};
  try {
    payload = (await response.json()) as ErrorPayload;
  } catch {
    // Provider gateways can return HTML; never expose it as an application message.
  }
  const kind = classify(response.status, payload.code);
  if (response.status === 401) window.dispatchEvent(new Event("lms:unauthorized"));
  return new ApiError(
    payload.message ?? defaultMessage(kind),
    kind,
    response.status,
    payload.request_id,
  );
}

function classify(status: number, code?: string): ApiErrorKind {
  if (status === 401) return "authentication";
  if (status === 403) return "forbidden";
  if (status === 422) return "validation";
  if (status === 429) return "rate_limited";
  if (code === "database_unavailable") return "database_unavailable";
  if ([502, 503, 504].includes(status)) return "service_warming";
  if (status === 409) return "conflict";
  return "unexpected";
}

function defaultMessage(kind: ApiErrorKind): string {
  const messages: Record<ApiErrorKind, string> = {
    authentication: "Please sign in again.",
    conflict: "The request conflicts with the latest library state.",
    database_unavailable: "The database is unavailable and may need an owner to resume it.",
    forbidden: "Your account cannot perform this action.",
    network: "The service could not be reached.",
    rate_limited: "Too many requests were made. Please wait and retry.",
    service_warming: "The library service is waking up. This can take about a minute.",
    unexpected: "An unexpected service response was received.",
    validation: "Review the highlighted information and try again.",
  };
  return messages[kind];
}

function normalizeError(reason: unknown): ApiError {
  return reason instanceof ApiError
    ? reason
    : new ApiError("The service could not be reached.", "network");
}

function readCookie(name: string): string | undefined {
  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix))
    ?.slice(prefix.length);
}

async function delay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (!milliseconds) return;
  await new Promise<void>((resolve, reject) => {
    const finish = () => {
      signal?.removeEventListener("abort", abort);
      resolve();
    };
    const timer = window.setTimeout(finish, milliseconds);
    const abort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Request cancelled", "AbortError"));
    };
    signal?.addEventListener("abort", abort, { once: true });
  });
}
