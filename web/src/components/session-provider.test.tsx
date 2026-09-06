import { act, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { apiRequest } from "@/lib/api/request";

import { SessionProvider, useSession } from "./session-provider";

vi.mock("@/lib/api/request", () => ({ apiRequest: vi.fn() }));

const requestMock = vi.mocked(apiRequest);
const principal = {
  user_id: 8,
  display_name: "Mina Reader",
  username: "mina.reader",
  role: "member" as const,
};

function Probe() {
  const session = useSession();
  return (
    <div>
      <span>{session.phase}</span>
      <span>{session.principal?.display_name}</span>
      <button type="button" onClick={() => void session.login("mina.reader", "password")}>
        Login
      </button>
      <button type="button" onClick={() => void session.logout()}>
        Logout
      </button>
    </div>
  );
}

beforeEach(() => requestMock.mockReset());

test("recovers an existing browser session", async () => {
  requestMock.mockResolvedValue({ principal, csrf_token: "csrf", expires_at: "2030-01-01" });
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(await screen.findByText("Mina Reader")).toBeInTheDocument();
  expect(screen.getByText("signed-in")).toBeInTheDocument();
});

test("clears local principal state when another request reports unauthorized", async () => {
  requestMock.mockResolvedValue({ principal, csrf_token: "csrf", expires_at: "2030-01-01" });
  render(<SessionProvider><Probe /></SessionProvider>);
  expect(await screen.findByText("Mina Reader")).toBeInTheDocument();
  act(() => window.dispatchEvent(new Event("lms:unauthorized")));
  expect(screen.getByText("signed-out")).toBeInTheDocument();
});
