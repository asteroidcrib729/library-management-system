import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { CatalogPanel } from "./catalog-panel";

const execute = vi.hoisted(() => vi.fn());
const retry = vi.hoisted(() => vi.fn());
const useCommand = vi.hoisted(() => vi.fn());
const useResource = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/use-command", () => ({ useCommand }));
vi.mock("@/hooks/use-resource", () => ({ useResource }));

beforeEach(() => {
  execute.mockReset().mockResolvedValue(undefined);
  retry.mockReset();
  useCommand.mockReset().mockReturnValue({
    execute,
    retry: vi.fn(),
    state: { phase: "idle" },
  });
  useResource.mockReset().mockReturnValue({ phase: "ready", data: [], retry });
});

test("lets staff add a physical copy through the inventory API", () => {
  render(
    <CatalogPanel principal={{
      user_id: 2,
      display_name: "Lina Librarian",
      username: "lina.staff",
      role: "librarian",
    }} />,
  );

  fireEvent.change(screen.getByLabelText("Catalog book ID"), { target: { value: "17" } });
  fireEvent.change(screen.getAllByLabelText("Barcode")[0], { target: { value: "COPY-17-A" } });
  fireEvent.click(screen.getByRole("button", { name: "Add copy" }));

  expect(execute).toHaveBeenCalledWith(expect.objectContaining({
    method: "POST",
    path: "/api/v1/catalog/books/17/copies",
    body: { barcode: "COPY-17-A" },
  }));
});

test("does not expose inventory controls to a member", () => {
  render(
    <CatalogPanel principal={{
      user_id: 3,
      display_name: "Mina Member",
      username: "mina.member",
      role: "member",
    }} />,
  );

  expect(screen.queryByRole("heading", { name: "Catalog inventory" })).not.toBeInTheDocument();
});
