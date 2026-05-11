import { nextApiClient } from "@next/core/api/client";

import type {
  AIQueryHistoryDetail,
  AIQueryHistorySummary,
  AIQueryHistoryUpdatePayload,
  AIQueryResponse,
  ChartSuggestion,
  VisualizationSuggestion,
} from "./types";

interface RawAIQueryResponse {
  query_id: number | null;
  answer: string;
  sql: string | null;
  rows: Record<string, unknown>[] | null;
  columns: string[] | null;
  chart_suggestion: unknown;
  visualization_suggestion: unknown;
  sql_analysis: AIQueryResponse["sql_analysis"];
  metadata: AIQueryResponse["metadata"];
}

function normalizeChartSuggestion(value: unknown): ChartSuggestion | null {
  if (!value) {
    return null;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? { type: trimmed } : null;
  }

  if (typeof value !== "object") {
    return null;
  }

  const candidate = value as Record<string, unknown>;
  const typeValue = candidate.type ?? candidate.chart_type ?? candidate.kind ?? candidate.name;
  if (typeof typeValue !== "string" || !typeValue.trim()) {
    return null;
  }

  const pickString = (field: unknown): string | null =>
    typeof field === "string" && field.trim() ? field.trim() : null;

  return {
    type: typeValue.trim(),
    x_axis: pickString(candidate.x_axis ?? candidate.xAxis),
    y_axis: pickString(candidate.y_axis ?? candidate.yAxis),
    explanation: pickString(candidate.explanation ?? candidate.reason),
  };
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

function normalizeQueryResponse(data: RawAIQueryResponse): AIQueryResponse {
  return {
    query_id: data.query_id,
    answer: data.answer,
    sql: data.sql,
    rows: data.rows ?? [],
    columns: data.columns ?? [],
    chart_suggestion: normalizeChartSuggestion(data.chart_suggestion),
    visualization_suggestion: normalizeVisualizationSuggestion(data.visualization_suggestion),
    sql_analysis: data.sql_analysis,
    metadata: data.metadata,
  };
}

export async function queryDatasetWithAI(datasetId: number, question: string): Promise<AIQueryResponse> {
  const { data } = await nextApiClient.post<RawAIQueryResponse>("/ai/query", {
    dataset_id: datasetId,
    question,
  });

  return normalizeQueryResponse(data);
}

export async function listAIQueryHistory(datasetId?: number): Promise<AIQueryHistorySummary[]> {
  const { data } = await nextApiClient.get<AIQueryHistorySummary[]>("/ai/history", {
    params: datasetId ? { dataset_id: datasetId } : undefined,
  });

  return data;
}

export async function getAIQueryHistoryDetail(queryId: number): Promise<AIQueryHistoryDetail> {
  const { data } = await nextApiClient.get<Omit<AIQueryHistoryDetail, "result"> & { result: RawAIQueryResponse | null }>(
    `/ai/history/${queryId}`,
  );

  return {
    ...data,
    result: data.result ? normalizeQueryResponse(data.result) : null,
  };
}

export async function updateAIQueryHistory(
  queryId: number,
  payload: AIQueryHistoryUpdatePayload,
): Promise<AIQueryHistoryDetail> {
  const normalizedPayload: AIQueryHistoryUpdatePayload = {};

  if ("title" in payload) {
    const trimmed = payload.title?.trim();
    normalizedPayload.title = trimmed ? trimmed.slice(0, 120) : null;
  }

  if ("is_favorite" in payload && typeof payload.is_favorite === "boolean") {
    normalizedPayload.is_favorite = payload.is_favorite;
  }

  const { data } = await nextApiClient.patch<Omit<AIQueryHistoryDetail, "result"> & { result: RawAIQueryResponse | null }>(
    `/ai/history/${queryId}`,
    normalizedPayload,
  );

  return {
    ...data,
    result: data.result ? normalizeQueryResponse(data.result) : null,
  };
}

export async function deleteAIQueryHistory(queryId: number): Promise<void> {
  await nextApiClient.delete(`/ai/history/${queryId}`);
}
