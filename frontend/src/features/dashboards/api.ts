import { nextApiClient } from "@next/core/api/client";
import type { AIQueryResponse, VisualizationSuggestion } from "@next/features/ai/types";
import type { InsightItem } from "@next/features/insights/types";

import type {
  CreateDashboardPayload,
  CreateDashboardWidgetPayload,
  DashboardChartType,
  DashboardDetail,
  DashboardExecutionStatus,
  DashboardFreshnessStatus,
  DashboardLayout,
  DashboardNarrative,
  DashboardSourceType,
  DashboardSummary,
  DashboardWidget,
  DashboardWidgetExecutionType,
  DashboardWidgetType,
} from "./types";

interface RawInsightSource {
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
  columns?: string[] | null;
  rows?: Record<string, unknown>[] | null;
  visualization_suggestion?: unknown;
}

interface RawDashboardWidget {
  id: number;
  dashboard_id: number;
  type: DashboardWidgetType;
  widget_type?: DashboardWidgetType | null;
  source_type: string;
  source_id?: number | null;
  execution_type?: DashboardWidgetExecutionType | null;
  execution_status?: DashboardExecutionStatus | null;
  chart_type?: DashboardChartType | null;
  query_sql?: string | null;
  layout?: Partial<DashboardLayout> | null;
  title?: string | null;
  config_json?: Record<string, unknown> | null;
  data_json?: Record<string, unknown>[] | Record<string, unknown> | null;
  last_run_at?: string | null;
  error_message?: string | null;
  insight_index?: number | null;
  has_snapshot?: boolean | null;
  using_snapshot?: boolean | null;
  snapshot_created_at?: string | null;
  source_changed?: boolean | null;
  created_at: string;
  source?: {
    query?: AIQueryResponse | null;
    insight?: RawInsightSource | null;
  } | null;
}

interface RawDashboardSummary extends DashboardSummary {}

interface RawDashboardDetail extends Omit<DashboardDetail, "widgets"> {
  widgets: RawDashboardWidget[];
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

function normalizeInsight(raw: RawInsightSource): InsightItem {
  const rows = raw.rows ?? raw.data ?? [];
  const summary = raw.summary?.trim() || raw.description?.trim() || "";

  return {
    id: raw.id?.trim() || `${raw.type}:${raw.metric ?? "metric"}:${raw.dimension ?? "dimension"}`,
    type: raw.type,
    title: raw.title,
    description: summary,
    summary,
    severity: raw.severity ?? "info",
    metric: raw.metric ?? null,
    dimension: raw.dimension ?? null,
    value: raw.value ?? null,
    confidence: typeof raw.confidence === "number" ? raw.confidence : 0.5,
    impact: typeof raw.impact === "number" ? raw.impact : 0.5,
    priority: raw.priority ?? "medium",
    sql: raw.sql ?? null,
    chart_suggestion: raw.chart_suggestion ?? null,
    chart_type: raw.chart_type ?? raw.chart_suggestion ?? "table",
    data: rows,
    columns: raw.columns ?? [],
    rows,
    visualization_suggestion: normalizeVisualizationSuggestion(raw.visualization_suggestion),
  };
}

function normalizeSourceType(sourceType: string): DashboardSourceType {
  if (sourceType === "query" || sourceType === "insight" || sourceType === "manual" || sourceType === "ask_ai") {
    return sourceType;
  }
  return "manual";
}

function normalizeFreshness(status: string): DashboardFreshnessStatus {
  if (status === "fresh" || status === "stale" || status === "failed" || status === "never_refreshed") {
    return status;
  }
  return "never_refreshed";
}

function normalizeLayout(layout: Partial<DashboardLayout> | null | undefined): DashboardLayout {
  return {
    column_span: layout?.column_span === 2 ? 2 : 1,
    order: typeof layout?.order === "number" ? layout.order : 0,
    use_snapshot: Boolean(layout?.use_snapshot),
    x: typeof layout?.x === "number" ? layout.x : 0,
    y: typeof layout?.y === "number" ? layout.y : 0,
    width: typeof layout?.width === "number" ? layout.width : 6,
    height: typeof layout?.height === "number" ? layout.height : 5,
  };
}

function normalizeWidget(raw: RawDashboardWidget): DashboardWidget {
  return {
    id: raw.id,
    dashboard_id: raw.dashboard_id,
    type: raw.type,
    widget_type: raw.widget_type ?? raw.type,
    source_type: normalizeSourceType(raw.source_type),
    source_id: raw.source_id ?? null,
    execution_type: raw.execution_type ?? "snapshot",
    execution_status: raw.execution_status ?? "never_run",
    chart_type: raw.chart_type ?? null,
    query_sql: raw.query_sql ?? null,
    layout: normalizeLayout(raw.layout),
    title: raw.title ?? null,
    config_json: raw.config_json ?? null,
    data_json: raw.data_json ?? null,
    last_run_at: raw.last_run_at ?? null,
    error_message: raw.error_message ?? null,
    insight_index: raw.insight_index ?? null,
    has_snapshot: Boolean(raw.has_snapshot),
    using_snapshot: Boolean(raw.using_snapshot),
    snapshot_created_at: raw.snapshot_created_at ?? null,
    source_changed: Boolean(raw.source_changed),
    created_at: raw.created_at,
    source: {
      query: raw.source?.query ?? null,
      insight: raw.source?.insight ? normalizeInsight(raw.source.insight) : null,
    },
  };
}

function normalizeSummary(raw: RawDashboardSummary): DashboardSummary {
  return {
    ...raw,
    dataset_id: raw.dataset_id ?? null,
    auto_refresh_enabled: Boolean(raw.auto_refresh_enabled),
    refresh_interval_minutes: typeof raw.refresh_interval_minutes === "number" ? raw.refresh_interval_minutes : null,
    last_successful_refresh_at: raw.last_successful_refresh_at ?? null,
    next_refresh_at: raw.next_refresh_at ?? null,
    freshness_status: normalizeFreshness(raw.freshness_status),
  };
}

function normalizeDetail(raw: RawDashboardDetail): DashboardDetail {
  return {
    id: raw.id,
    name: raw.name,
    dataset_id: raw.dataset_id ?? null,
    auto_refresh_enabled: Boolean(raw.auto_refresh_enabled),
    refresh_interval_minutes: typeof raw.refresh_interval_minutes === "number" ? raw.refresh_interval_minutes : null,
    last_successful_refresh_at: raw.last_successful_refresh_at ?? null,
    next_refresh_at: raw.next_refresh_at ?? null,
    freshness_status: normalizeFreshness(raw.freshness_status),
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    widgets: (raw.widgets ?? []).map(normalizeWidget),
  };
}

function normalizeNarrative(narrative: DashboardNarrative | null | undefined): DashboardNarrative {
  return {
    summary: narrative?.summary ?? "",
    key_findings: narrative?.key_findings ?? [],
    risks_or_caveats: narrative?.risks_or_caveats ?? [],
    recommended_next_actions: narrative?.recommended_next_actions ?? [],
    stale_or_failed_widgets: narrative?.stale_or_failed_widgets ?? [],
  };
}

export async function listDashboards(): Promise<DashboardSummary[]> {
  const { data } = await nextApiClient.get<RawDashboardSummary[]>("/dashboards");
  return data.map(normalizeSummary);
}

export async function createDashboard(payload: CreateDashboardPayload): Promise<DashboardDetail> {
  const { data } = await nextApiClient.post<RawDashboardDetail>("/dashboards", {
    name: payload.name.trim(),
    dataset_id: payload.dataset_id ?? null,
  });
  return normalizeDetail(data);
}

function normalizeWidgetPayload(payload: CreateDashboardWidgetPayload): Record<string, unknown> {
  return {
    ...payload,
    widget_type: payload.widget_type ?? payload.type,
    execution_type: payload.execution_type ?? undefined,
    chart_type: payload.chart_type ?? undefined,
    query_sql: payload.query_sql ?? undefined,
    title: payload.title?.trim() || undefined,
    config_json: payload.config_json ?? undefined,
    data_json: payload.data_json ?? undefined,
    source_id: payload.source_id ?? undefined,
    insight_index: payload.insight_index ?? undefined,
    save_snapshot: payload.save_snapshot ?? undefined,
    layout: payload.layout
      ? {
          column_span: payload.layout.column_span,
          order: payload.layout.order,
          use_snapshot: payload.layout.use_snapshot,
          x: payload.layout.x,
          y: payload.layout.y,
          width: payload.layout.width,
          height: payload.layout.height,
        }
      : undefined,
  };
}

export async function getDashboard(dashboardId: number): Promise<DashboardDetail> {
  const { data } = await nextApiClient.get<RawDashboardDetail>(`/dashboards/${dashboardId}`);
  return normalizeDetail(data);
}

export async function createDashboardWidget(
  dashboardId: number,
  payload: CreateDashboardWidgetPayload,
): Promise<DashboardDetail> {
  const { data } = await nextApiClient.post<RawDashboardDetail>(
    `/dashboards/${dashboardId}/widgets`,
    normalizeWidgetPayload(payload),
  );
  return normalizeDetail(data);
}

export async function getDashboardNarrative(dashboardId: number): Promise<DashboardNarrative> {
  const { data } = await nextApiClient.get<DashboardNarrative>(`/dashboards/${dashboardId}/narrative`);
  return normalizeNarrative(data);
}

export async function refreshDashboard(dashboardId: number): Promise<DashboardDetail> {
  const { data } = await nextApiClient.post<RawDashboardDetail>(`/dashboards/${dashboardId}/refresh`);
  return normalizeDetail(data);
}

export async function refreshDashboardWidget(dashboardId: number, widgetId: number): Promise<DashboardWidget> {
  const { data } = await nextApiClient.post<RawDashboardWidget>(`/dashboards/${dashboardId}/widgets/${widgetId}/refresh`);
  return normalizeWidget(data);
}
