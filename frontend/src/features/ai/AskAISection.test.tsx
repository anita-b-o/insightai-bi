import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AskAIComposer } from "@next/features/ai/components/ask-ai-composer";

vi.mock("@next/features/ai/api", () => ({
  deleteAIQueryHistory: vi.fn(),
  getAIQueryHistoryDetail: vi.fn(),
  listAIQueryHistory: vi.fn(),
  queryDatasetWithAI: vi.fn(),
  updateAIQueryHistory: vi.fn(),
}));

vi.mock("@next/features/dashboards/api", async () => {
  const actual = await vi.importActual("@next/features/dashboards/api");
  return {
    ...actual,
    createDashboard: vi.fn(),
    createDashboardWidget: vi.fn(),
    listDashboards: vi.fn(),
  };
});

import { getAIQueryHistoryDetail, listAIQueryHistory, queryDatasetWithAI } from "@next/features/ai/api";
import { createDashboardWidget, listDashboards } from "@next/features/dashboards/api";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function renderAskAIComposer() {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AskAIComposer datasetId={7} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AskAISection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listAIQueryHistory).mockResolvedValue([]);
    vi.mocked(getAIQueryHistoryDetail).mockResolvedValue({
      id: 11,
      dataset_id: 7,
      question: "Show revenue by month",
      title: null,
      is_favorite: false,
      generated_sql: "SELECT month, SUM(revenue) AS total_revenue FROM sales GROUP BY month",
      execution_time_ms: 42,
      created_at: "2026-04-30T12:00:00+00:00",
      updated_at: "2026-04-30T12:00:00+00:00",
      result: {
        query_id: 11,
        answer: "Revenue by month is increasing.",
        sql: "SELECT month, SUM(revenue) AS total_revenue FROM sales GROUP BY month",
        rows: [{ month: "2026-04", total_revenue: 120 }],
        columns: ["month", "total_revenue"],
        chart_suggestion: { type: "bar" },
        visualization_suggestion: {
          type: "bar",
          x: "month",
          y: "total_revenue",
          label: null,
          value: null,
          reason: "Grouped metric by category.",
        },
        sql_analysis: {
          is_aggregated: true,
          aggregation_functions: ["SUM"],
          group_by_columns: ["month"],
          selected_columns: ["month", "total_revenue"],
          has_group_by: true,
          has_order_by: false,
          has_limit: false,
        },
        metadata: {
          dataset_id: 7,
          dataset_name: "Sales",
          column_count: 4,
          model: "gpt-4.1-mini",
          fallback_used: false,
          cache_hit: false,
        },
      },
    });
    vi.mocked(listDashboards).mockResolvedValue([
      {
        id: 3,
        name: "Ops",
        dataset_id: 7,
        auto_refresh_enabled: false,
        refresh_interval_minutes: null,
        last_successful_refresh_at: null,
        next_refresh_at: null,
        freshness_status: "never_refreshed",
        created_at: "2026-04-30T12:00:00+00:00",
        updated_at: "2026-04-30T12:00:00+00:00",
        widget_count: 1,
      },
    ]);
  });

  it("saves Ask AI results as query widgets", async () => {
    vi.mocked(queryDatasetWithAI).mockResolvedValue({
      query_id: 11,
      answer: "Revenue by month is increasing.",
      sql: "SELECT month, SUM(revenue) AS total_revenue FROM sales GROUP BY month",
      rows: [{ month: "2026-04", total_revenue: 120 }],
      columns: ["month", "total_revenue"],
      chart_suggestion: { type: "bar" },
      visualization_suggestion: {
        type: "bar",
        x: "month",
        y: "total_revenue",
        label: null,
        value: null,
        reason: "Grouped metric by category.",
      },
      sql_analysis: {
        is_aggregated: true,
        aggregation_functions: ["SUM"],
        group_by_columns: ["month"],
        selected_columns: ["month", "total_revenue"],
        has_group_by: true,
        has_order_by: false,
        has_limit: false,
      },
      metadata: {
        dataset_id: 7,
        dataset_name: "Sales",
        column_count: 4,
        model: "gpt-4.1-mini",
        fallback_used: false,
        cache_hit: false,
      },
    });
    vi.mocked(createDashboardWidget).mockResolvedValue({
      id: 3,
      name: "Ops",
      dataset_id: 7,
      auto_refresh_enabled: false,
      refresh_interval_minutes: null,
      last_successful_refresh_at: null,
      next_refresh_at: null,
      freshness_status: "never_refreshed",
      created_at: "2026-04-30T12:00:00+00:00",
      updated_at: "2026-04-30T12:00:00+00:00",
      widgets: [],
    });

    renderAskAIComposer();

    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "Show revenue by month" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask AI" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save chart to dashboard" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save chart to dashboard" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save widget" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save widget" }));

    await waitFor(() => {
      expect(createDashboardWidget).toHaveBeenCalled();
    });

    expect(createDashboardWidget).toHaveBeenCalledWith(
      3,
      expect.objectContaining({
        type: "chart",
        source_type: "query",
        source_id: 11,
        execution_type: "query",
        query_sql: "SELECT month, SUM(revenue) AS total_revenue FROM sales GROUP BY month",
        data_json: [{ month: "2026-04", total_revenue: 120 }],
      }),
    );
  }, 10_000);
});
