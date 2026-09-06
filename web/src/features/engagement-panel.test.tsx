import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { EngagementPanel } from "./engagement-panel";

const execute = vi.hoisted(() => vi.fn());
const useCommand = vi.hoisted(() => vi.fn());
const useResource = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/use-command", () => ({ useCommand }));
vi.mock("@/hooks/use-resource", () => ({ useResource }));

beforeEach(() => {
  execute.mockReset().mockResolvedValue(undefined);
  useCommand.mockReset().mockReturnValue({
    execute,
    retry: vi.fn(),
    state: { phase: "idle" },
  });
  useResource.mockReset();
});

test("lets staff link an approved request to its acquired catalog title", () => {
  useResource
    .mockReturnValueOnce({
      phase: "ready",
      retry: vi.fn(),
      data: [{
        username: "mina.member",
        acquired_book_title: null,
        request: {
          id: 9,
          title: "The Left Hand of Darkness",
          author: "Ursula K. Le Guin",
          status: "approved",
          review_note: null,
        },
      }],
    })
    .mockReturnValueOnce({ phase: "ready", retry: vi.fn(), data: [] });

  render(
    <EngagementPanel principal={{
      user_id: 2,
      display_name: "Lina Librarian",
      username: "lina.staff",
      role: "librarian",
    }} />,
  );
  fireEvent.change(screen.getByLabelText("Catalog book ID"), { target: { value: "41" } });
  fireEvent.click(screen.getByRole("button", { name: "Mark acquired" }));

  expect(execute).toHaveBeenCalledWith(expect.objectContaining({
    path: "/api/v1/engagement/book-requests/9/acquire",
    body: { book_id: 41 },
  }));
});
