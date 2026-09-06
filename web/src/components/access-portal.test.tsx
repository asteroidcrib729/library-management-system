import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AccessPortal } from "./access-portal";

const login = vi.hoisted(() => vi.fn());
const replace = vi.hoisted(() => vi.fn());
const useSession = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/components/session-provider", () => ({ useSession }));

beforeEach(() => {
  login.mockReset().mockResolvedValue(undefined);
  replace.mockReset();
  useSession.mockReset().mockReturnValue({
    phase: "signed-out",
    login,
    refresh: vi.fn(),
  });
});

test("completes the labeled sign-in journey and enters the dashboard", async () => {
  render(<AccessPortal />);

  expect(screen.getByRole("tab", { name: "Sign in" })).toHaveAttribute("aria-selected", "true");
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "mina.member" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse" } });
  fireEvent.click(screen.getByRole("button", { name: "Enter dashboard" }));

  await waitFor(() => expect(login).toHaveBeenCalledWith("mina.member", "correct horse"));
  expect(replace).toHaveBeenCalledWith("/dashboard");
});

test("exposes registration and bootstrap as keyboard-operable tabs", () => {
  render(<AccessPortal />);

  fireEvent.click(screen.getByRole("tab", { name: "Join" }));
  expect(screen.getByRole("heading", { name: "Create your membership" })).toBeInTheDocument();
  expect(screen.getByLabelText("Display name")).toHaveAttribute("autocomplete", "name");

  fireEvent.click(screen.getByRole("tab", { name: "First setup" }));
  expect(screen.getByRole("heading", { name: "Create the first administrator" })).toBeInTheDocument();
});
