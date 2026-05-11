import { describe, expect, it } from "vitest";

import type { AIQueryResponse } from "@next/features/ai/types";
import { parseNumericValue, resolveChartModel } from "./ai-result-chart.utils";

const baseResult: AIQueryResponse = {
  query_id: 1,
  answer: "Answer",
  sql: "select 1",
  rows: [],
  columns: [],
  chart_suggestion: null,
  visualization_suggestion: null,
  preferred_chart_type: null,
  preferred_chart_metric: null,
  preferred_chart_dimension: null,
  sql_analysis: null,
  metadata: null,
};

describe("ai-result-chart utils", () => {
  it("parses numeric strings", () => {
    expect(parseNumericValue("29,266")).toBe(29266);
    expect(parseNumericValue("29266")).toBe(29266);
    expect(parseNumericValue("3.52")).toBe(3.52);
    expect(parseNumericValue("not-a-number")).toBeNull();
  });

  it("uses backend bar suggestion when renderable", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { category: "Bosques", total: 1200 },
        { category: "Pastizales", total: 800 },
      ],
      columns: ["category", "total"],
      visualization_suggestion: {
        type: "bar",
        x: "category",
        y: "total",
        label: null,
        value: null,
        reason: "backend bar",
      },
    });

    expect(model?.type).toBe("bar");
    expect(model?.xKey).toBe("category");
    expect(model?.yKey).toBe("total");
  });

  it("respects forced table insights and renders no chart", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { stat: "Minimum", value: 10 },
        { stat: "Average", value: 22 },
        { stat: "Maximum", value: 45 },
      ],
      columns: ["stat", "value"],
      preferred_chart_type: "table",
      preferred_chart_metric: "revenue",
      preferred_chart_dimension: null,
    });

    expect(model).toBeNull();
  });

  it("respects forced scatter insights instead of inferring pie", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { x_value: 10, y_value: 15 },
        { x_value: 20, y_value: 30 },
        { x_value: 30, y_value: 28 },
        { x_value: 40, y_value: 42 },
        { x_value: 50, y_value: 39 },
      ],
      columns: ["x_value", "y_value"],
      preferred_chart_type: "scatter",
      preferred_chart_dimension: "x_value",
      preferred_chart_metric: "y_value",
    });

    expect(model?.type).toBe("scatter");
    expect(model?.xKey).toBe("x_value");
    expect(model?.yKey).toBe("y_value");
  });

  it("infers pie chart for low-cardinality category plus numeric metric", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { cobertura: "Bosques", superficie: "29,266" },
        { cobertura: "Pastizales", superficie: "12000" },
        { cobertura: "Humedales", superficie: "5400" },
      ],
      columns: ["cobertura", "superficie"],
    });

    expect(model?.type).toBe("pie");
  });

  it("infers line chart for temporal plus numeric metric", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { periodo: "2026-01-01", total: "10" },
        { periodo: "2026-02-01", total: "25" },
      ],
      columns: ["periodo", "total"],
    });

    expect(model?.type).toBe("line");
  });

  it("returns null for unchartable data", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [{ estado: "ok", detalle: "sin metrica" }],
      columns: ["estado", "detalle"],
    });

    expect(model).toBeNull();
  });

  it("returns null for pie data with negative values", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { category: "IGN", metric: -22.08 },
        { category: "Gamespot", metric: -22.13 },
      ],
      columns: ["category", "metric"],
      preferred_chart_type: "pie",
    });

    expect(model).toBeNull();
  });

  it("returns null for pie data with one repeated label", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { label: "IGN", metric: 22.08 },
        { label: "IGN", metric: 22.13 },
      ],
      columns: ["label", "metric"],
      preferred_chart_type: "pie",
    });

    expect(model).toBeNull();
  });

  it("keeps valid forced pie charts renderable", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [
        { category: "Bosques", total: 1200 },
        { category: "Pastizales", total: 800 },
      ],
      columns: ["category", "total"],
      preferred_chart_type: "pie",
      preferred_chart_dimension: "category",
      preferred_chart_metric: "total",
    });

    expect(model?.type).toBe("pie");
  });

  it("keeps valid forced bar charts renderable", () => {
    const model = resolveChartModel({
      ...baseResult,
      rows: [{ stat: "Minimum", value: 10 }],
      columns: ["stat", "value"],
      preferred_chart_type: "bar",
      preferred_chart_dimension: "stat",
      preferred_chart_metric: "value",
    });

    expect(model?.type).toBe("bar");
  });
});
