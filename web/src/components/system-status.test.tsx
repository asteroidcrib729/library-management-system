import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { SystemStatus } from "./system-status";

const getHealth = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: getHealth },
}));

beforeEach(() => {
  getHealth.mockReset();
});

test("shows that the local API is available after a successful liveness check", async () => {
  getHealth.mockResolvedValue({ data: { status: "ok" } });
  render(<SystemStatus />);
  expect(screen.getByText("Checking local API")).toBeInTheDocument();
  expect(await screen.findByText("Local API available")).toBeInTheDocument();
});

test("shows a recoverable unavailable state when the liveness request fails", async () => {
  getHealth.mockRejectedValue(new TypeError("offline"));
  render(<SystemStatus />);
  expect(await screen.findByText("Local API is not running")).toBeInTheDocument();
});
