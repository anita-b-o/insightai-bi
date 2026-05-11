import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import { alpha } from "@mui/material/styles";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip, Stack, Typography } from "@mui/material";

import { StatusBadge } from "@next/components/ui/status-badge";
import { SurfaceCard } from "@next/components/ui/surface-card";
import { AIResultChart, EmptyChartState, getChartRenderState } from "@next/features/ai/components/ai-result-chart";
import { AIResultTable } from "@next/features/ai/components/ai-result-table";
import type { AIQueryResponse, VisualizationSuggestion } from "@next/features/ai/types";
import { tokens } from "@next/theme/tokens";

import { formatDashboardDateTime, widgetExecutionLabel, widgetExecutionTone, type DashboardWidget as DashboardWidgetModel } from "../types";

function buildRows(widget: DashboardWidgetModel): Record<string, unknown>[] {
  if (Array.isArray(widget.data_json)) {
    return widget.data_json;
  }
  if (widget.source.query?.rows?.length) {
    return widget.source.query.rows;
  }
  if (widget.source.insight?.rows?.length) {
    return widget.source.insight.rows;
  }
  if (widget.source.insight?.data?.length) {
    return widget.source.insight.data;
  }
  return [];
}

function buildColumns(widget: DashboardWidgetModel, rows: Record<string, unknown>[]): string[] {
  if (widget.source.query?.columns?.length) {
    return widget.source.query.columns;
  }
  if (widget.source.insight?.columns?.length) {
    return widget.source.insight.columns;
  }
  return rows[0] ? Object.keys(rows[0]) : [];
}

function buildVisualizationSuggestion(widget: DashboardWidgetModel): VisualizationSuggestion | null {
  const config = widget.config_json;
  if (config && typeof config === "object") {
    const type = typeof config.type === "string" ? config.type : widget.chart_type;
    if (type === "bar" || type === "line" || type === "pie" || type === "scatter" || type === "table_only" || type === "table") {
      return {
        type: type === "table" ? "table_only" : type,
        x: typeof config.x === "string" ? config.x : null,
        y: typeof config.y === "string" ? config.y : null,
        label: typeof config.label === "string" ? config.label : null,
        value: typeof config.value === "string" ? config.value : null,
        reason: typeof config.reason === "string" ? config.reason : null,
      };
    }
  }

  return widget.source.query?.visualization_suggestion ?? widget.source.insight?.visualization_suggestion ?? null;
}

function buildResult(widget: DashboardWidgetModel): AIQueryResponse | null {
  const rows = buildRows(widget);
  const columns = buildColumns(widget, rows);
  if (!rows.length || !columns.length) {
    return null;
  }

  return {
    query_id: widget.source.query?.query_id ?? widget.source_id ?? null,
    answer: widget.source.query?.answer ?? widget.source.insight?.summary ?? widget.title ?? "Dashboard widget",
    sql: widget.query_sql ?? widget.source.query?.sql ?? widget.source.insight?.sql ?? null,
    rows,
    columns,
    chart_suggestion: widget.chart_type ? { type: widget.chart_type } : null,
    visualization_suggestion: buildVisualizationSuggestion(widget),
    preferred_chart_type: widget.chart_type,
    preferred_chart_metric: widget.source.insight?.metric ?? null,
    preferred_chart_dimension: widget.source.insight?.dimension ?? null,
    sql_analysis: widget.source.query?.sql_analysis ?? null,
    metadata: widget.source.query?.metadata ?? null,
  };
}

export function DashboardWidget({
  widget,
  isBusy = false,
  error,
  readOnly = false,
  onRefresh,
}: {
  widget: DashboardWidgetModel;
  isBusy?: boolean;
  error?: string | null;
  readOnly?: boolean;
  onRefresh: (widget: DashboardWidgetModel) => void;
}) {
  const result = buildResult(widget);
  const summary = widget.source.insight?.summary ?? null;
  const title = widget.title ?? widget.source.insight?.title ?? "Dashboard widget";
  const chartState = result ? getChartRenderState(result) : { status: "no-data" as const, model: null };
  const hasTable = Boolean(result?.rows.length && result?.columns.length);
  const showChart = chartState.status === "supported";
  const prefersTable = chartState.status === "unsupported" && hasTable;
  const widgetAlert = error ?? widget.error_message ?? null;
  const widgetAlertSeverity = error ? "error" : "warning";

  return (
    <SurfaceCard tone="panel" padding="sm">
      <Stack spacing={1.25} sx={{ height: "100%", minHeight: 0 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.2} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "flex-start" }}>
          <Stack spacing={0.85} sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={0.9} useFlexGap flexWrap="wrap" alignItems="center">
              <Chip
                size="small"
                label={widget.widget_type}
                sx={{
                  borderRadius: tokens.radius.xs,
                  backgroundColor: tokens.color.bg.surface,
                }}
              />
              <StatusBadge label={widgetExecutionLabel(widget.execution_status)} tone={widgetExecutionTone(widget.execution_status)} />
              {widget.last_run_at ? (
                <Typography variant="caption" color="text.secondary">
                  Last run {formatDashboardDateTime(widget.last_run_at)}
                </Typography>
              ) : null}
            </Stack>
            <Typography variant="h6">{title}</Typography>
            {summary ? (
              <Typography variant="body2" color="text.secondary">
                {summary}
              </Typography>
            ) : null}
          </Stack>

          {readOnly ? null : (
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshRoundedIcon />}
              disabled={isBusy}
              aria-label="Refresh"
              onClick={() => onRefresh(widget)}
            >
              {isBusy ? "Refreshing..." : "Refresh"}
            </Button>
          )}
        </Stack>

        {widgetAlert ? (
          <Alert severity={widgetAlertSeverity} variant="outlined" aria-live="polite">
            {widgetAlert}
          </Alert>
        ) : null}

        {!result ? (
          <Box
            sx={{
              py: 2.6,
              borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              This widget does not have renderable rows yet. Use the refresh action to populate it.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={0.95} sx={{ minHeight: 0 }}>
            {result.answer ? (
              <Box
                sx={{
                  px: 0,
                  py: 0.72,
                  borderRadius: 0,
                  backgroundColor: "transparent",
                  borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.26)}`,
                }}
              >
                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                  {result.answer}
                </Typography>
              </Box>
            ) : null}

            {showChart ? <AIResultChart result={result} /> : null}
            {!showChart && prefersTable ? <EmptyChartState /> : null}

            {hasTable ? (
              <Box sx={{ minWidth: 0, borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.24)}`, pt: 0.8 }}>
                <AIResultTable columns={result.columns} rows={result.rows} maxHeight={224} compact={showChart || widget.type !== "table"} title="Supporting result" />
              </Box>
            ) : (
              <Box
                sx={{
                  py: 2,
                  borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.24)}`,
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  No table or visualization is available for this widget yet.
                </Typography>
              </Box>
            )}

            {result.sql ? (
              <Accordion
                disableGutters
                elevation={0}
                sx={{
                  border: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
                  borderRadius: `${tokens.radius.xs}px !important`,
                  backgroundColor: tokens.color.bg.surface,
                  "&::before": { display: "none" },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 0, px: 1.25, py: 0.1 }} aria-label="View generated SQL">
                  <Typography variant="subtitle2">View generated SQL</Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ pt: 0, px: 1.25, pb: 1.15 }}>
                  <Typography component="pre" variant="body2" sx={{ m: 0, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
                    {result.sql}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ) : null}
          </Stack>
        )}
      </Stack>
    </SurfaceCard>
  );
}
