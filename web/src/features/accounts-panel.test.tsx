import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AccountsPanel } from "./accounts-panel";

const execute = vi.hoisted(() => vi.fn());
const useCommand = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/use-command", () => ({ useCommand }));

beforeEach(() => {
  execute.mockReset().mockResolvedValue(undefined);
  useCommand.mockReset().mockReturnValue({
    execute,
    retry: vi.fn(),
    state: { phase: "idle" },
  });
});

test("requires confirmation before deactivating an account", () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<AccountsPanel />);
  fireEvent.change(screen.getAllByLabelText("Username")[1], {
    target: { value: "reader.one" },
  });

  fireEvent.click(screen.getByRole("button", { name: "Deactivate account" }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(execute).not.toHaveBeenCalled();

  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Deactivate account" }));
  expect(execute).toHaveBeenCalledWith(expect.objectContaining({
    path: "/api/v1/accounts/deactivate",
    body: { username: "reader.one" },
  }));
});
