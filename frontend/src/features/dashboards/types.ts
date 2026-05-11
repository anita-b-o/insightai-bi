import type { AIQueryResponse, VisualizationSuggestion } from "@next/features/ai/types";
import type { InsightItem } from "@next/features/insights/types";

export type DashboardWidgetType = "chart" | "table" | "insight";
export type DashboardChartType = "bar" | "line" | "pie" | "scatter" | "table";
export type DashboardSourceType = "ask_ai" | "query" | "insight" | "manual";
export type DashboardExecutionStatus = "never_run" | "success" | "failed";
export type DashboardWidgetExecutionType = "snapshot" | "query" | "insight";
export type DashboardFreshnessStatus = "fresh" | "stale" | "failed" | "never_refreshed";

export interface DashboardLayout {
  column_span: 1 | 2;
  order: number;
  use_snapshot: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DashboardSummary {
  id: number;
  name: string;
  dataset_id: number | null;
  auto_refresh_enabled: boolean;
  refresh_interval_minutes: number | null;
  last_successful_refresh_at: string | null;
  next_refresh_at: string | null;
  freshness_status: DashboardFreshnessStatus;
  created_at: string;
  updated_at: string;
  widget_count: number;
}

export interface DashboardNarrative {
  summary: string;
  key_findings: string[];
  risks_or_caveats: string[];
  recommended_next_actions: string[];
  stale_or_failed_widgets: string[];
}

export interface DashboardWidgetResolvedSource {
  query: AIQueryResponse | null;
  insight: InsightItem | null;
}

export interface DashboardWidget {
  id: number;
  dashboard_id: number;
  type: DashboardWidgetType;
  widget_type: DashboardWidgetType;
  source_type: DashboardSourceType;
  source_id: number | null;
  execution_type: DashboardWidgetExecutionType;
  execution_status: DashboardExecutionStatus;
  chart_type: DashboardChartType | null;
  query_sql: string | null;
  layout: DashboardLayout;
  title: string | null;
  config_json: Record<string, unknown> | null;
  data_json: Record<string, unknown>[] | Record<string, unknown> | null;
  last_run_at: string | null;
  error_message: string | null;
  insight_index: number | null;
  has_snapshot: boolean;
  using_snapshot: boolean;
  snapshot_created_at: string | null;
  source_changed: boolean;
  created_at: string;
  source: DashboardWidgetResolvedSource;
}

export interface DashboardDetail extends Omit<DashboardSummary, "widget_count"> {
  widgets: DashboardWidget[];
}

export interface CreateDashboardPayload {
  name: string;
  dataset_id?: number | null;
}

export interface CreateDashboardWidgetPayload {
  type: DashboardWidgetType;
  widget_type?: DashboardWidgetType;
  source_type: DashboardSourceType;
  source_id?: number | null;
  execution_type?: DashboardWidgetExecutionType | null;
  chart_type?: DashboardChartType | null;
  query_sql?: string | null;
  layout?: Partial<DashboardLayout>;
  title?: string | null;
  config_json?: Record<string, unknown> | null;
  data_json?: Record<string, unknown>[] | Record<string, unknown> | null;
  insight_index?: number | null;
  save_snapshot?: boolean;
}

export function formatDashboardDateTime(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}

export function formatDashboardInterval(minutes: number | null): string {
  if (minutes === 360) {
    return "6 h";
  }
  if (minutes === 1440) {
    return "24 h";
  }
  if (typeof minutes === "number") {
    return `${minutes} min`;
  }
  return "Off";
}

export function formatFreshnessLabel(status: DashboardFreshnessStatus): string {
  if (status === "never_refreshed") {
    return "Never refreshed";
  }
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function dashboardFreshnessTone(status: DashboardFreshnessStatus): "success" | "warning" | "error" | "info" {
  if (status === "fresh") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  if (status === "stale" || status === "never_refreshed") {
    return "warning";
  }
  return "info";
}

export function widgetExecutionLabel(status: DashboardExecutionStatus): string {
  if (status === "never_run") {
    return "Never run";
  }
  if (status === "failed") {
    return "Failed";
  }
  return "Success";
}

export function widgetExecutionTone(status: DashboardExecutionStatus): "success" | "warning" | "error" | "info" {
  if (status === "success") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  if (status === "never_run") {
    return "warning";
  }
  return "info";
}

export function buildWidgetVisualizationConfig(
  suggestion: VisualizationSuggestion | null | undefined,
): Record<string, unknown> | null {
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
