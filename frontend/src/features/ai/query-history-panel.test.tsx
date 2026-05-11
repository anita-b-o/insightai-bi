import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QueryHistoryPanel } from "@next/features/ai/components/query-history-panel";

const entry = {
  id: 1,
  dataset_id: 3,
  question: "What are the top products?",
  title: null,
  is_favorite: false,
  generated_sql: "select * from sales",
  execution_time_ms: 42,
  created_at: "2026-04-28T10:00:00+00:00",
  updated_at: "2026-04-28T10:00:00+00:00",
};

describe("QueryHistoryPanel", () => {
  it("shows title when present and falls back to question", () => {
    render(
      <QueryHistoryPanel
        entries={[entry, { ...entry, id: 2, title: "Pinned revenue trend" }]}
        selectedQueryId={1}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onToggleFavorite={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText("What are the top products?")).toBeInTheDocument();
    expect(screen.getByText("Pinned revenue trend")).toBeInTheDocument();
  });

  it("triggers favorite, rename and delete actions", async () => {
    const onToggleFavorite = vi.fn().mockResolvedValue(undefined);
    const onRename = vi.fn().mockResolvedValue(undefined);
    const onDelete = vi.fn().mockResolvedValue(undefined);

    render(
      <QueryHistoryPanel
        entries={[entry]}
        selectedQueryId={1}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onToggleFavorite={onToggleFavorite}
        onRename={onRename}
        onDelete={onDelete}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Mark favorite" }));
    await waitFor(() => expect(onToggleFavorite).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(onDelete).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Rename" }));
    fireEvent.change(screen.getByPlaceholderText("Custom title"), { target: { value: "Revenue snapshot" } });
    fireEvent.click(screen.getByRole("button", { name: "Save title" }));

    await waitFor(() =>
      expect(onRename).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }), "Revenue snapshot"),
    );
  });
});
