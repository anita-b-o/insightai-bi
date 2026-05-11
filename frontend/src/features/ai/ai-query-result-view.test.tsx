import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AIQueryResponse } from "@next/features/ai/types";
import { AIResultView } from "@next/features/ai/components/ai-result-view";

const baseResult: AIQueryResponse = {
  query_id: 7,
  answer: "Revenue is concentrated in a few products.",
  sql: "SELECT product_name, SUM(revenue) AS total_revenue FROM sales GROUP BY product_name",
  rows: [{ product_name: "A", total_revenue: 1000 }],
  columns: ["product_name", "total_revenue"],
  chart_suggestion: null,
  visualization_suggestion: {
    type: "bar",
    x: "product_name",
    y: "total_revenue",
    label: null,
    value: null,
    reason: "Detected an aggregated result grouped by a category, which fits a bar chart.",
  },
  sql_analysis: {
    is_aggregated: true,
    aggregation_functions: ["SUM"],
    group_by_columns: ["product_name"],
    selected_columns: ["product_name", "total_revenue"],
    has_group_by: true,
    has_order_by: false,
    has_limit: false,
  },
  metadata: {
    dataset_id: 1,
    dataset_name: "Sales",
    column_count: 12,
    model: "gpt-4.1-mini",
    fallback_used: false,
    cache_hit: false,
  },
};

describe("AIQueryResultView", () => {
  it("shows aggregated result metadata", () => {
    render(<AIResultView result={baseResult} />);

    expect(screen.getByText("Aggregated result")).toBeInTheDocument();
    expect(screen.getByText("View generated SQL")).toBeInTheDocument();
  });

  it("shows raw rows metadata and fallback reason", () => {
    render(
      <AIResultView
        result={{
          ...baseResult,
          visualization_suggestion: {
            type: "table_only",
            reason: "This query returns raw rows. Aggregating the data may produce a better chart.",
            x: null,
            y: null,
            label: null,
            value: null,
          },
          sql_analysis: {
            is_aggregated: false,
            aggregation_functions: [],
            group_by_columns: [],
            selected_columns: ["product_name", "revenue"],
            has_group_by: false,
            has_order_by: false,
            has_limit: true,
          },
        }}
      />,
    );

    expect(screen.getByText("Raw rows")).toBeInTheDocument();
    expect(
      screen.queryByText("This query returns raw rows. Aggregating the data may produce a better chart."),
    ).not.toBeInTheDocument();
  });

  it("renders the suggested visualization and keeps the table visible", () => {
    render(<AIResultView result={baseResult} />);

    expect(screen.getByText("Suggested visualization")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });
});
