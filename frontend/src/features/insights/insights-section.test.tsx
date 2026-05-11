import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InsightsSection } from "@next/features/insights/components/insights-section";

vi.mock("@next/features/insights/api", () => ({
  generateDatasetInsights: vi.fn(),
  getLatestDatasetInsights: vi.fn(),
  refreshDatasetInsights: vi.fn(),
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

import { generateDatasetInsights, getLatestDatasetInsights } from "@next/features/insights/api";
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

function renderInsightsSection() {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <InsightsSection datasetId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const emptyNarrative = {
  summary: "",
  key_findings: [],
  risks_or_caveats: [],
  recommended_next_questions: [],
};

describe("InsightsSection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listDashboards).mockResolvedValue([
      {
        id: 4,
        name: "Insights",
        dataset_id: 1,
        auto_refresh_enabled: false,
        refresh_interval_minutes: null,
        last_successful_refresh_at: null,
        next_refresh_at: null,
        freshness_status: "never_refreshed",
        created_at: "2026-04-30T12:00:00+00:00",
        updated_at: "2026-04-30T12:00:00+00:00",
        widget_count: 0,
      },
    ]);
  });

  it("shows empty state when there is no persisted run", async () => {
    vi.mocked(getLatestDatasetInsights).mockRejectedValue({ response: { status: 404 } });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("No insights generated yet")).toBeInTheDocument();
    });
  });

  it("loads the latest persisted run on open", async () => {
    vi.mocked(getLatestDatasetInsights).mockResolvedValue({
      run_id: 5,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T18:30:00+00:00",
      is_stale: true,
      error_message: null,
      narrative: emptyNarrative,
      insights: [
        {
          id: "trend:revenue:month",
          type: "trend",
          title: "Revenue increased over time",
          summary: "Summed revenue increased over time.",
          description: "Summed revenue increased over time.",
          severity: "info",
          metric: "revenue",
          dimension: "month",
          value: 120,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT month, SUM(revenue) AS metric FROM sales GROUP BY month",
          chart_suggestion: "line",
          chart_type: "line",
          columns: ["period", "metric"],
          rows: [{ period: "2026-04-01", metric: 120 }],
          data: [],
          visualization_suggestion: null,
        },
      ],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("Revenue increased over time")).toBeInTheDocument();
    });
    expect(screen.getByText("Dataset changed since these insights were generated.")).toBeInTheDocument();
    expect(screen.getByText("Metric revenue")).toBeInTheDocument();
    expect(screen.getByText("View supporting SQL")).toBeInTheDocument();
  });

  it("generates insights when requested", async () => {
    vi.mocked(getLatestDatasetInsights)
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({
        run_id: 6,
        dataset_id: 1,
        dataset_name: "Sales",
        status: "success",
        generated_at: "2026-04-29T18:40:00+00:00",
        is_stale: false,
        error_message: null,
        narrative: emptyNarrative,
        insights: [
          {
            id: "distribution:revenue:all",
            type: "distribution",
            title: "Revenue distribution snapshot",
            summary: "Revenue ranges from 10 to 100.",
            description: "Revenue ranges from 10 to 100.",
            severity: "info",
            metric: "revenue",
            dimension: null,
            value: 55,
            confidence: 0.5,
            impact: 0.5,
            priority: "medium",
            sql: "SELECT MIN(revenue), AVG(revenue), MAX(revenue) FROM sales",
            chart_suggestion: "bar",
            chart_type: "bar",
            columns: ["stat", "value"],
            rows: [{ stat: "Minimum", value: 10 }],
            data: [],
            visualization_suggestion: null,
          },
        ],
      });
    vi.mocked(generateDatasetInsights).mockResolvedValue({
      run_id: 6,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T18:40:00+00:00",
      is_stale: false,
      error_message: null,
      narrative: emptyNarrative,
      insights: [
        {
          id: "distribution:revenue:all",
          type: "distribution",
          title: "Revenue distribution snapshot",
          summary: "Revenue ranges from 10 to 100.",
          description: "Revenue ranges from 10 to 100.",
          severity: "info",
          metric: "revenue",
          dimension: null,
          value: 55,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT MIN(revenue), AVG(revenue), MAX(revenue) FROM sales",
          chart_suggestion: "bar",
          chart_type: "bar",
          columns: ["stat", "value"],
          rows: [{ stat: "Minimum", value: 10 }],
          data: [],
          visualization_suggestion: null,
        },
      ],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate insights" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate insights" }));

    await waitFor(() => {
      expect(screen.getByText("Revenue distribution snapshot")).toBeInTheDocument();
    });
    expect(generateDatasetInsights).toHaveBeenCalledWith(1);
  });

  it("does not render a suggested visualization for outlier label-metric rows", async () => {
    vi.mocked(getLatestDatasetInsights).mockResolvedValue({
      run_id: 7,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T18:45:00+00:00",
      is_stale: false,
      error_message: null,
      narrative: emptyNarrative,
      insights: [
        {
          id: "outlier:metric:label",
          type: "outlier",
          title: "Review score outliers",
          summary: "Two outlets fall well below baseline.",
          description: "Two outlets fall well below baseline.",
          severity: "warning",
          metric: "metric",
          dimension: "label",
          value: null,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT label, metric FROM scores WHERE is_outlier = true",
          chart_suggestion: "pie",
          chart_type: "pie",
          columns: ["label", "metric"],
          rows: [
            { label: "IGN", metric: -22.08 },
            { label: "IGN", metric: -22.13 },
          ],
          data: [],
          visualization_suggestion: {
            type: "pie",
            label: "label",
            value: "metric",
            x: null,
            y: null,
            reason: "This fits a pie chart.",
          },
        },
      ],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("Review score outliers")).toBeInTheDocument();
    });

    expect(screen.queryByText("Suggested visualization")).not.toBeInTheDocument();
  });

  it("renders valid suggested visualizations for non-outlier insights", async () => {
    vi.mocked(getLatestDatasetInsights).mockResolvedValue({
      run_id: 8,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T18:50:00+00:00",
      is_stale: false,
      error_message: null,
      narrative: emptyNarrative,
      insights: [
        {
          id: "distribution:revenue:channel",
          type: "distribution",
          title: "Channel mix",
          summary: "Revenue is concentrated in two channels.",
          description: "Revenue is concentrated in two channels.",
          severity: "info",
          metric: "revenue",
          dimension: "channel",
          value: 2000,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT channel, SUM(revenue) AS revenue FROM sales GROUP BY channel",
          chart_suggestion: "pie",
          chart_type: "pie",
          columns: ["channel", "revenue"],
          rows: [
            { channel: "Retail", revenue: 1200 },
            { channel: "Wholesale", revenue: 800 },
          ],
          data: [],
          visualization_suggestion: {
            type: "pie",
            label: "channel",
            value: "revenue",
            x: null,
            y: null,
            reason: "Positive category totals can be shown as a pie chart.",
          },
        },
        {
          id: "distribution:value:stat",
          type: "distribution",
          title: "Revenue summary",
          summary: "Minimum revenue is 10.",
          description: "Minimum revenue is 10.",
          severity: "info",
          metric: "value",
          dimension: "stat",
          value: 10,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT 'Minimum' AS stat, 10 AS value",
          chart_suggestion: "bar",
          chart_type: "bar",
          columns: ["stat", "value"],
          rows: [{ stat: "Minimum", value: 10 }],
          data: [],
          visualization_suggestion: {
            type: "bar",
            x: "stat",
            y: "value",
            label: null,
            value: null,
            reason: "A categorical metric comparison fits a bar chart.",
          },
        },
      ],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("Channel mix")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Suggested visualization")).toHaveLength(2);
  });

  it("renders executive summary content above insight cards", async () => {
    vi.mocked(getLatestDatasetInsights).mockResolvedValue({
      run_id: 9,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T19:00:00+00:00",
      is_stale: false,
      error_message: null,
      narrative: {
        summary: "Revenue is concentrated in Retail and moves in line with order volume.",
        key_findings: [
          "Retail has the highest total revenue.",
          "Revenue and order count show a positive relationship.",
        ],
        risks_or_caveats: ["Some columns are constant across the dataset."],
        recommended_next_questions: ["How does revenue evolve over time by channel?"],
      },
      insights: [
        {
          id: "top_performer:revenue:channel",
          type: "top_performer",
          title: "Retail leads revenue",
          summary: "Retail has the highest total revenue.",
          description: "Retail has the highest total revenue.",
          severity: "info",
          metric: "revenue",
          dimension: "channel",
          value: 1200,
          confidence: 0.5,
          impact: 0.5,
          priority: "medium",
          sql: "SELECT channel, SUM(revenue) AS metric FROM sales GROUP BY channel",
          chart_suggestion: "bar",
          chart_type: "bar",
          columns: ["category", "metric"],
          rows: [{ category: "Retail", metric: 1200 }],
          data: [],
          visualization_suggestion: null,
        },
      ],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("Executive summary")).toBeInTheDocument();
    });

    expect(screen.getByText("Revenue is concentrated in Retail and moves in line with order volume.")).toBeInTheDocument();
    expect(screen.getByText("Key findings")).toBeInTheDocument();
    expect(screen.getAllByText("Retail has the highest total revenue.").length).toBeGreaterThan(0);
    expect(screen.getByText("Caveats")).toBeInTheDocument();
    expect(screen.getByText("Some columns are constant across the dataset.")).toBeInTheDocument();
    expect(screen.getByText("Recommended next questions")).toBeInTheDocument();
    expect(screen.getByText("How does revenue evolve over time by channel?")).toBeInTheDocument();
  });

  it("renders backend errors cleanly", async () => {
    vi.mocked(getLatestDatasetInsights).mockRejectedValue({
      response: { status: 500, data: { detail: "Dataset is empty" } },
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByText("Dataset is empty")).toBeInTheDocument();
    });
  });

  it("saves insights as insight widgets", async () => {
    vi.mocked(getLatestDatasetInsights).mockResolvedValue({
      run_id: 12,
      dataset_id: 1,
      dataset_name: "Sales",
      status: "success",
      generated_at: "2026-04-29T19:10:00+00:00",
      is_stale: false,
      error_message: null,
      narrative: emptyNarrative,
      insights: [
        {
          id: "top_performer:revenue:channel",
          type: "top_performer",
          title: "Retail leads revenue",
          summary: "Retail has the highest total revenue.",
          description: "Retail has the highest total revenue.",
          severity: "info",
          metric: "revenue",
          dimension: "channel",
          value: 1200,
          confidence: 0.9,
          impact: 0.8,
          priority: "high",
          sql: "SELECT channel, SUM(revenue) AS metric FROM sales GROUP BY channel",
          chart_suggestion: "bar",
          chart_type: "bar",
          columns: ["channel", "metric"],
          rows: [{ channel: "Retail", metric: 1200 }],
          data: [{ channel: "Retail", metric: 1200 }],
          visualization_suggestion: {
            type: "bar",
            x: "channel",
            y: "metric",
            label: null,
            value: null,
            reason: "Grouped metric by category.",
          },
        },
      ],
    });
    vi.mocked(createDashboardWidget).mockResolvedValue({
      id: 4,
      name: "Insights",
      dataset_id: 1,
      auto_refresh_enabled: false,
      refresh_interval_minutes: null,
      last_successful_refresh_at: null,
      next_refresh_at: null,
      freshness_status: "never_refreshed",
      created_at: "2026-04-30T12:00:00+00:00",
      updated_at: "2026-04-30T12:00:00+00:00",
      widgets: [],
    });

    renderInsightsSection();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save to dashboard" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save to dashboard" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save widget" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save widget" }));

    await waitFor(() => {
      expect(createDashboardWidget).toHaveBeenCalled();
    });

    expect(createDashboardWidget).toHaveBeenCalledWith(
      4,
      expect.objectContaining({
        type: "insight",
        source_type: "insight",
        source_id: 12,
        execution_type: "insight",
        title: "Retail leads revenue",
      }),
    );
  });
});
