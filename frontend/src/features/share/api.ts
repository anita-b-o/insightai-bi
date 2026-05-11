import { nextApiClient } from "@next/core/api/client";
import type { DashboardNarrative, DashboardWidget } from "@next/features/dashboards/types";
import type { InsightItem } from "@next/features/insights/types";
import type { AIQueryResponse, VisualizationSuggestion } from "@next/features/ai/types";

import type {
  CreateDashboardShareLinkPayload,
  DashboardShareLink,
  DashboardShareLinkCreateResponse,
  SharedDashboardDetail,
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

interface RawDashboardWidget extends Omit<DashboardWidget, "source"> {
  source?: {
    query?: AIQueryResponse | null;
    insight?: RawInsightSource | null;
  } | null;
}

interface RawDashboardShareLink extends Omit<DashboardShareLink, never> {}

interface RawSharedDashboardDetail extends Omit<SharedDashboardDetail, "widgets" | "narrative"> {
  widgets: RawDashboardWidget[];
  narrative?: DashboardNarrative | null;
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

function normalizeNarrative(narrative: DashboardNarrative | null | undefined): DashboardNarrative {
  return {
    summary: narrative?.summary ?? "",
    key_findings: narrative?.key_findings ?? [],
    risks_or_caveats: narrative?.risks_or_caveats ?? [],
    recommended_next_actions: narrative?.recommended_next_actions ?? [],
    stale_or_failed_widgets: narrative?.stale_or_failed_widgets ?? [],
  };
}

function normalizeShareLink(link: RawDashboardShareLink): DashboardShareLink {
  return {
    id: link.id,
    dashboard_id: link.dashboard_id,
    expires_at: link.expires_at ?? null,
    revoked_at: link.revoked_at ?? null,
    created_at: link.created_at,
    share_url: link.share_url,
  };
}

function normalizeSharedDashboard(detail: RawSharedDashboardDetail): SharedDashboardDetail {
  return {
    id: detail.id,
    name: detail.name,
    freshness_status:
      detail.freshness_status === "fresh" ||
      detail.freshness_status === "stale" ||
      detail.freshness_status === "failed" ||
      detail.freshness_status === "never_refreshed"
        ? detail.freshness_status
        : "never_refreshed",
    last_successful_refresh_at: detail.last_successful_refresh_at ?? null,
    next_refresh_at: detail.next_refresh_at ?? null,
    narrative: normalizeNarrative(detail.narrative),
    widgets: (detail.widgets ?? []).map((widget) => ({
      ...widget,
      source_id: widget.source_id ?? null,
      query_sql: widget.query_sql ?? null,
      title: widget.title ?? null,
      config_json: widget.config_json ?? null,
      data_json: widget.data_json ?? null,
      last_run_at: widget.last_run_at ?? null,
      error_message: widget.error_message ?? null,
      insight_index: widget.insight_index ?? null,
      has_snapshot: Boolean(widget.has_snapshot),
      using_snapshot: Boolean(widget.using_snapshot),
      snapshot_created_at: widget.snapshot_created_at ?? null,
      source_changed: Boolean(widget.source_changed),
      source: {
        query: widget.source?.query ?? null,
        insight: widget.source?.insight ? normalizeInsight(widget.source.insight) : null,
      },
    })),
  };
}

export async function listDashboardShareLinks(dashboardId: number): Promise<DashboardShareLink[]> {
  const { data } = await nextApiClient.get<RawDashboardShareLink[]>(`/dashboards/${dashboardId}/share-links`);
  return data.map(normalizeShareLink);
}

export async function createDashboardShareLink(
  dashboardId: number,
  payload: CreateDashboardShareLinkPayload,
): Promise<DashboardShareLinkCreateResponse> {
  const { data } = await nextApiClient.post<DashboardShareLinkCreateResponse>(`/dashboards/${dashboardId}/share-links`, {
    expires_at: payload.expires_at ?? null,
  });

  return {
    ...normalizeShareLink(data),
    token: data.token,
  };
}

export async function revokeDashboardShareLink(dashboardId: number, shareId: number): Promise<void> {
  await nextApiClient.delete(`/dashboards/${dashboardId}/share-links/${shareId}`);
}

export async function getSharedDashboard(token: string): Promise<SharedDashboardDetail> {
  const { data } = await nextApiClient.get<RawSharedDashboardDetail>(`/public/dashboards/${encodeURIComponent(token)}`);
  return normalizeSharedDashboard(data);
}
