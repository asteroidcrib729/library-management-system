import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { apiRequest, createIdempotencyKey } from "./request";
import { ApiError } from "./types";

beforeEach(() => {
  document.cookie = "lms_csrf=csrf-value; path=/";
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

test("adds credentials, CSRF, and the retained idempotency key to commands", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await apiRequest("/api/v1/example", {
    method: "POST",
    body: { title: "Example" },
    idempotencyKey: "stable-command-key",
  });

  const [, init] = fetchMock.mock.calls[0];
  const headers = new Headers(init?.headers);
  expect(init?.credentials).toBe("include");
  expect(headers.get("X-CSRF-Token")).toBe("csrf-value");
  expect(headers.get("Idempotency-Key")).toBe("stable-command-key");
});

test("shares simultaneous safe reads", async () => {
  let resolveFetch!: (response: Response) => void;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
    () => new Promise<Response>((resolve) => (resolveFetch = resolve)),
  );

  const first = apiRequest<{ value: number }>("/api/v1/shared");
  const second = apiRequest<{ value: number }>("/api/v1/shared");
  resolveFetch(new Response(JSON.stringify({ value: 4 }), { status: 200 }));

  await expect(Promise.all([first, second])).resolves.toEqual([{ value: 4 }, { value: 4 }]);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("classifies a paused database separately from a waking gateway", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        code: "database_unavailable",
        message: "The database is temporarily unavailable.",
        request_id: "request-7",
      }),
      { status: 503 },
    ),
  );

  const request = apiRequest("/api/v1/finance/fines", { method: "POST" });

  await expect(request).rejects.toMatchObject({
    kind: "database_unavailable",
    requestId: "request-7",
  } satisfies Partial<ApiError>);
});

test("announces an unauthorized response so session state can be cleared", async () => {
  const unauthorized = vi.fn();
  window.addEventListener("lms:unauthorized", unauthorized, { once: true });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ code: "authentication_required", message: "Sign in." }), {
      status: 401,
    }),
  );

  await expect(apiRequest("/api/v1/private", { method: "POST" })).rejects.toMatchObject({
    kind: "authentication",
  });
  expect(unauthorized).toHaveBeenCalledOnce();
});

test("bounds automatic retries while a safe read is waking", async () => {
  vi.useFakeTimers();
  const onWarming = vi.fn();
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    new Response("<h1>Starting</h1>", {
      status: 503,
      headers: { "Content-Type": "text/html" },
    }),
  );

  const request = apiRequest("/api/v1/waking", { onWarming });
  const result = expect(request).rejects.toMatchObject({ kind: "service_warming" });
  await vi.runAllTimersAsync();
  await result;

  expect(fetchMock).toHaveBeenCalledTimes(4);
  expect(onWarming).toHaveBeenCalledTimes(3);
});

test("cancels an in-flight read without converting it into a network error", async () => {
  const controller = new AbortController();
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) =>
    new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => {
        reject(new DOMException("Fetch cancelled", "AbortError"));
      });
    }),
  );

  const request = apiRequest("/api/v1/cancelled", { signal: controller.signal });
  controller.abort();

  await expect(request).rejects.toMatchObject({ name: "AbortError" });
});

describe("command keys", () => {
  test("creates a distinct key for each user action", () => {
    expect(createIdempotencyKey()).not.toBe(createIdempotencyKey());
  });
});
