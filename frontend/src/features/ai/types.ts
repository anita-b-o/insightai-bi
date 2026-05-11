export type VisualizationType = "bar" | "line" | "pie" | "scatter" | "table_only";

export interface ChartSuggestion {
  type: string;
  x_axis?: string | null;
  y_axis?: string | null;
  explanation?: string | null;
}

export interface VisualizationSuggestion {
  type: VisualizationType;
  x?: string | null;
  y?: string | null;
  label?: string | null;
  value?: string | null;
  reason?: string | null;
}

export interface SQLAnalysisResult {
  is_aggregated: boolean;
  aggregation_functions: string[];
  group_by_columns: string[];
  selected_columns: string[];
  has_group_by: boolean;
  has_order_by: boolean;
  has_limit: boolean;
}

export interface AIQueryMetadata {
  dataset_id: number;
  dataset_name: string;
  column_count: number;
  model: string;
  fallback_used: boolean;
  cache_hit: boolean;
}

export interface AIQueryResponse {
  query_id: number | null;
  answer: string;
  sql: string | null;
  rows: Record<string, unknown>[];
  columns: string[];
  chart_suggestion: ChartSuggestion | null;
  visualization_suggestion: VisualizationSuggestion | null;
  preferred_chart_type?: "bar" | "line" | "pie" | "scatter" | "table" | null;
  preferred_chart_metric?: string | null;
  preferred_chart_dimension?: string | null;
  sql_analysis: SQLAnalysisResult | null;
  metadata: AIQueryMetadata | null;
}

export interface AIQueryHistorySummary {
  id: number;
  dataset_id: number;
  question: string;
  title: string | null;
  is_favorite: boolean;
  generated_sql: string | null;
  execution_time_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface AIQueryHistoryDetail extends AIQueryHistorySummary {
  result: AIQueryResponse | null;
}

export interface AIQueryHistoryUpdatePayload {
  title?: string | null;
  is_favorite?: boolean;
}

export function formatQueryTitle(entry: Pick<AIQueryHistorySummary, "title" | "question">) {
  return entry.title?.trim() || entry.question;
}

export function formatResultColumnLabel(column: string): string {
  return column
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function isIsoDateString(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}/.test(value) && !Number.isNaN(new Date(value).getTime());
}

export function formatResultCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }

  if (typeof value === "number") {
    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
    }).format(value);
  }

  if (typeof value === "string" && isIsoDateString(value)) {
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
    }).format(new Date(value));
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export function buildVisualizationConfig(suggestion: VisualizationSuggestion | null | undefined): Record<string, unknown> | null {
  if (!suggestion) {
    return null;
  }

  return {
    type: suggestion.type,
    x: suggestion.x ?? null,
    y: suggestion.y ?? null,
    label: suggestion.label ?? null,
    value: suggestion.value ?? null,
    reason: suggestion.reason ?? null,
  };
}
