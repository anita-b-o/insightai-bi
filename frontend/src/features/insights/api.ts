import type { VisualizationSuggestion } from "@next/features/ai/types";
import { nextApiClient } from "@next/core/api/client";

import type { InsightItem, InsightNarrative, InsightsResponse } from "./types";

interface RawInsightItem {
  id?: string | null;
  type: string;
  title: string;
  summary?: string | null;
  description?: string | null;
  severity?: "info" | "warning" | "critical" | null;
  metric?: string | null;
  dimension?: string | null;
  value?: string | number | null;
  confidence?: number | null;
  impact?: number | null;
  priority?: "high" | "medium" | "low" | null;
  sql?: string | null;
  chart_suggestion?: "bar" | "line" | "pie" | "scatter" | "table" | null;
  chart_type?: "bar" | "line" | "pie" | "scatter" | "table" | null;
  data?: Record<string, unknown>[] | null;
  columns: string[] | null;
  rows: Record<string, unknown>[] | null;
  visualization_suggestion: unknown;
}

interface RawInsightsResponse {
  run_id: number | null;
  dataset_id: number;
  dataset_name: string;
  status: "success" | "failed";
  generated_at: string;
  is_stale: boolean;
  error_message: string | null;
  insights: RawInsightItem[] | null;
  narrative?: {
    summary?: string | null;
    key_findings?: string[] | null;
    risks_or_caveats?: string[] | null;
    recommended_next_questions?: string[] | null;
  } | null;
}

function normalizeVisualizationSuggestion(value: unknown): VisualizationSuggestion | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const candidate = value as Record<string, unknown>;
  const typeValue = candidate.type;
  if (typeValue !== "bar" && typeValue !== "line" && typeValue !== "pie" && typeValue !== "scatter" && typeValue !== "table_only") {
    return null;
  }

  const pickString = (field: unknown): string | null =>
    typeof field === "string" && field.trim() ? field.trim() : null;

  return {
    type: typeValue,
    x: pickString(candidate.x),
    y: pickString(candidate.y),
    label: pickString(candidate.label),
    value: pickString(candidate.value),
    reason: pickString(candidate.reason),
  };
}

function normalizeNarrative(value: RawInsightsResponse["narrative"]): InsightNarrative {
  return {
    summary: value?.summary?.trim() || "",
    key_findings: (value?.key_findings ?? []).filter((item): item is string => typeof item === "string" && item.trim().length > 0),
    risks_or_caveats: (value?.risks_or_caveats ?? []).filter((item): item is string => typeof item === "string" && item.trim().length > 0),
    recommended_next_questions: (value?.recommended_next_questions ?? []).filter(
      (item): item is string => typeof item === "string" && item.trim().length > 0,
    ),
  };
}

function normalizeInsight(item: RawInsightItem): InsightItem {
  const summary = item.summary?.trim() || item.description?.trim() || "";
  const rows = item.rows ?? item.data ?? [];
  const chartSuggestion = item.chart_suggestion ?? null;
  const chartType = item.chart_type ?? chartSuggestion ?? "table";

  return {
    id: item.id?.trim() || `${item.type}:${item.metric ?? "metric"}:${item.dimension ?? "dimension"}`,
    type: item.type,
    title: item.title,
    description: summary,
    summary,
    severity: item.severity ?? "info",
    metric: item.metric ?? null,
    dimension: item.dimension ?? null,
    value: item.value ?? null,
    confidence: typeof item.confidence === "number" ? item.confidence : 0.5,
    impact: typeof item.impact === "number" ? item.impact : 0.5,
    priority: item.priority ?? "medium",
    sql: item.sql ?? null,
    chart_suggestion: chartSuggestion,
    chart_type: chartType,
    data: rows,
    columns: item.columns ?? [],
    rows,
    visualization_suggestion: normalizeVisualizationSuggestion(item.visualization_suggestion),
  };
}

function normalizeResponse(data: RawInsightsResponse): InsightsResponse {
  return {
    run_id: data.run_id,
    dataset_id: data.dataset_id,
    dataset_name: data.dataset_name,
    status: data.status,
    generated_at: data.generated_at,
    is_stale: data.is_stale,
    error_message: data.error_message,
    insights: (data.insights ?? []).map(normalizeInsight),
    narrative: normalizeNarrative(data.narrative),
  };
}

export async function getLatestDatasetInsights(datasetId: number): Promise<InsightsResponse> {
  const { data } = await nextApiClient.get<RawInsightsResponse>(`/datasets/${datasetId}/insights`);
  return normalizeResponse(data);
}

export async function generateDatasetInsights(datasetId: number): Promise<InsightsResponse> {
  const { data } = await nextApiClient.post<RawInsightsResponse>(`/datasets/${datasetId}/insights/generate`);
  return normalizeResponse(data);
}

export async function refreshDatasetInsights(datasetId: number): Promise<InsightsResponse> {
  const { data } = await nextApiClient.post<RawInsightsResponse>(`/datasets/${datasetId}/insights/generate`);
  return normalizeResponse(data);
}
