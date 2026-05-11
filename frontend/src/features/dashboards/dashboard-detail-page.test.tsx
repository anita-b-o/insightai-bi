import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@next/features/dashboards/api", async () => {
  const actual = await vi.importActual("@next/features/dashboards/api");
  return {
    ...actual,
    getDashboard: vi.fn(),
    getDashboardNarrative: vi.fn(),
    refreshDashboard: vi.fn(),
    refreshDashboardWidget: vi.fn(),
  };
});

vi.mock("@next/features/dashboards/components/dashboard-grid", () => ({
  DashboardGrid: ({
    widgets,
    renderWidget,
  }: {
    widgets: Array<{ id: number }>;
    renderWidget: (widget: { id: number }) => unknown;
  }) => (
    <div data-testid="dashboard-grid">
      {widgets.map((widget) => (
        <div key={widget.id}>{renderWidget(widget)}</div>
      ))}
    </div>
  ),
}));

vi.mock("@next/features/ai/components/ai-result-chart", () => ({
  AIResultChart: () => (
    <div data-testid="ai-result-chart">
      <span>Suggested visualization</span>
    </div>
  ),
  EmptyChartState: () => <div data-testid="empty-chart-state">Suggested visualization</div>,
  getChartRenderState: (result: { preferred_chart_type?: string | null; rows?: unknown[]; columns?: string[] }) => {
    if (result.preferred_chart_type === "table" || !result.rows?.length || !result.columns?.length) {
      return { status: "unsupported", model: null };
    }
    return { status: "supported", model: { type: result.preferred_chart_type ?? "bar" } };
  },
}));

vi.mock("@next/features/ai/components/ai-result-table", () => ({
  AIResultTable: ({
    title,
    columns,
  }: {
    title?: string;
    columns: string[];
  }) => (
    <div data-testid="ai-result-table">
      {title ? <span>{title}</span> : null}
      <span>{columns.join(",")}</span>
    </div>
  ),
}));

import {
  getDashboard,
  getDashboardNarrative,
  refreshDashboard,
  refreshDashboardWidget,
} from "@next/features/dashboards/api";
import { NextDashboardDetailPage } from "@next/pages/dashboard-detail-page";

function makeDashboard(overrides: Record<string, unknown> = {}) {
  return {
    id: 3,
    name: "Ops",
    dataset_id: 7,
    auto_refresh_enabled: true,
    refresh_interval_minutes: 60,
    last_successful_refresh_at: "2026-04-30T12:10:00+00:00",
    next_refresh_at: "2026-04-30T13:10:00+00:00",
    freshness_status: "fresh",
    created_at: "2026-04-30T12:00:00+00:00",
    updated_at: "2026-04-30T12:00:00+00:00",
    widgets: [
      {
        id: 9,
        dashboard_id: 3,
        type: "chart",
        widget_type: "chart",
        source_type: "query",
        source_id: 12,
        execution_type: "query",
        execution_status: "success",
        chart_type: "bar",
        query_sql: "SELECT month, SUM(revenue) AS total_revenue FROM sales GROUP BY month",
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
    ...overrides,
  };
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function renderPage() {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/dashboards/3"]}>
        <Routes>
          <Route path="/dashboards/:dashboardId" element={<NextDashboardDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NextDashboardDetailPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getDashboardNarrative).mockResolvedValue({
      summary: "Ops contains one active revenue widget.",
      key_findings: ["Revenue by month is active as a bar query widget with 1 row of current data."],
      risks_or_caveats: [],
      recommended_next_actions: [],
      stale_or_failed_widgets: [],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the dashboard workspace and widgets", async () => {
    vi.mocked(getDashboard).mockResolvedValue(makeDashboard());

    renderPage();

    expect(await screen.findByRole("heading", { name: "Ops" })).toBeInTheDocument();

    expect(screen.getByText("Active dashboard")).toBeInTheDocument();
    expect(screen.getAllByText("Revenue by month").length).toBeGreaterThan(0);
    expect(screen.getByTestId("dashboard-grid")).toBeInTheDocument();
    expect(screen.getByText("Current interpretation")).toBeInTheDocument();
    expect(screen.getByText("Ops contains one active revenue widget.")).toBeInTheDocument();
  });

  it("refreshes the dashboard", async () => {
    vi.mocked(getDashboard).mockResolvedValue(makeDashboard());
    vi.mocked(refreshDashboard).mockResolvedValue(makeDashboard());

    renderPage();

    expect(await screen.findByRole("button", { name: "Refresh dashboard" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh dashboard" }));

    await waitFor(() => {
      expect(refreshDashboard).toHaveBeenCalledWith(3);
    });
  });

  it("refreshes a widget individually", async () => {
    vi.mocked(getDashboard).mockResolvedValue(makeDashboard());
    vi.mocked(refreshDashboardWidget).mockResolvedValue({
      ...makeDashboard().widgets[0],
      last_run_at: "2026-04-30T12:10:00+00:00",
      data_json: [{ month: "2026-05", total_revenue: 140 }],
      source: { query: null, insight: null },
    });

    renderPage();

    expect(await screen.findByRole("button", { name: "Refresh" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(refreshDashboardWidget).toHaveBeenCalledWith(3, 9);
    });
  });

  it("shows the empty state when a dashboard has no widgets", async () => {
    vi.mocked(getDashboard).mockResolvedValue(
      makeDashboard({
        widgets: [],
      }),
    );

    renderPage();

    expect(await screen.findByText("No widgets yet")).toBeInTheDocument();

    expect(
      screen.getByText("This dashboard exists, but it does not contain saved widgets yet. Save Ask AI results or insights from a dataset workspace."),
    ).toBeInTheDocument();
  });
});
