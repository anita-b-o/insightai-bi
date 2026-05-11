import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@next/features/dashboards/components/dashboard-grid", () => ({
  DashboardGrid: ({ widgets, renderWidget }: { widgets: Array<{ id: number }>; renderWidget: (widget: { id: number }) => unknown }) => (
    <div data-testid="shared-dashboard-grid">
      {widgets.map((widget) => (
        <div key={widget.id}>{renderWidget(widget)}</div>
      ))}
    </div>
  ),
}));

vi.mock("@next/features/share/api", async () => {
  const actual = await vi.importActual("@next/features/share/api");
  return {
    ...actual,
    getSharedDashboard: vi.fn(),
  };
});

import { getSharedDashboard } from "@next/features/share/api";
import { NextSharedDashboardPage } from "@next/pages/shared-dashboard-page";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/public/dashboards/5.signature"]}>
        <Routes>
          <Route path="/public/dashboards/:token" element={<NextSharedDashboardPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NextSharedDashboardPage", () => {
  it("renders the public read-only dashboard view", async () => {
    vi.mocked(getSharedDashboard).mockResolvedValue({
      id: 3,
      name: "Ops",
      freshness_status: "fresh",
      last_successful_refresh_at: "2026-04-30T12:10:00+00:00",
      next_refresh_at: "2026-04-30T13:10:00+00:00",
      narrative: {
        summary: "Ops contains one shared widget.",
        key_findings: ["Revenue by month is visible."],
        risks_or_caveats: [],
        recommended_next_actions: [],
        stale_or_failed_widgets: [],
      },
      widgets: [
        {
          id: 9,
          dashboard_id: 3,
          type: "chart",
          widget_type: "chart",
          source_type: "query",
          source_id: null,
          execution_type: "query",
          execution_status: "success",
          chart_type: "bar",
          query_sql: null,
          layout: { column_span: 1, order: 0, use_snapshot: false, x: 0, y: 0, width: 6, height: 4 },
          title: "Revenue by month",
          config_json: { type: "bar", x: "month", y: "total_revenue" },
          data_json: [{ month: "2026-04", total_revenue: 120 }],
          last_run_at: "2026-04-30T12:05:00+00:00",
          error_message: null,
          insight_index: null,
          has_snapshot: false,
          using_snapshot: false,
          snapshot_created_at: null,
          source_changed: false,
          created_at: "2026-04-30T12:00:00+00:00",
          source: { query: null, insight: null },
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Shared read-only dashboard\./)).toBeInTheDocument();
    });

    expect(screen.getByText("Ops")).toBeInTheDocument();
    expect(screen.getByText("Shared dashboard")).toBeInTheDocument();
    expect(screen.getByText("Current interpretation")).toBeInTheDocument();
    expect(screen.getByText("Ops contains one shared widget.")).toBeInTheDocument();
    expect(screen.getAllByText("Revenue by month").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Refresh" })).not.toBeInTheDocument();
  });
});
