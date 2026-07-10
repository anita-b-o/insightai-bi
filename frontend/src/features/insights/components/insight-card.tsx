import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import { Accordion, AccordionDetails, AccordionSummary, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { OpenSection } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";
import { AIResultChart, getChartRenderState } from "@next/features/ai/components/ai-result-chart";
import { AIResultTable } from "@next/features/ai/components/ai-result-table";
import type { AIQueryResponse } from "@next/features/ai/types";

import type { InsightItem } from "../types";

function toInsightResult(insight: InsightItem): AIQueryResponse {
  const rows = insight.data?.length ? insight.data : insight.rows;
  const visualizationSuggestion = insight.visualization_suggestion;
  const isExplicitScatterOutlier =
    insight.type === "outlier" &&
    (visualizationSuggestion?.type === "scatter" || insight.chart_type === "scatter");

  return {
    query_id: null,
    answer: insight.description,
    sql: insight.sql,
    rows,
    columns: insight.columns,
    chart_suggestion: insight.chart_type ? { type: insight.chart_type } : null,
    visualization_suggestion:
      visualizationSuggestion ??
      (insight.chart_type === "pie"
        ? { type: "pie", label: null, value: null, x: null, y: null, reason: null }
        : insight.chart_type === "table"
          ? { type: "table_only", x: null, y: null, label: null, value: null, reason: null }
          : insight.chart_type
            ? { type: insight.chart_type, x: null, y: null, label: null, value: null, reason: null }
            : null),
    preferred_chart_type: insight.type === "outlier" && !isExplicitScatterOutlier ? "table" : insight.chart_type,
    preferred_chart_metric: insight.metric,
    preferred_chart_dimension: insight.dimension,
    sql_analysis: null,
    metadata: null,
  };
}

function getAccent(insight: InsightItem) {
  if (insight.severity === "critical") {
    return tokens.color.accent.red;
  }
  if (insight.priority === "high") {
    return tokens.color.accent.amber;
  }
  if (insight.type === "trend") {
    return tokens.color.accent.cyan;
  }
  return tokens.color.accent.blue;
}

function severityTone(severity: InsightItem["severity"]): "default" | "info" | "warning" | "error" {
  if (severity === "critical") {
    return "error";
  }
  if (severity === "warning") {
    return "warning";
  }
  if (severity === "info") {
    return "info";
  }
  return "default";
}

export function InsightCard({
  insight,
  onSave,
}: {
  insight: InsightItem;
  onSave?: () => void;
}) {
  const accent = getAccent(insight);
  const result = toInsightResult(insight);
  const hasRows = result.columns.length > 0 && result.rows.length > 0;
  const chartState = hasRows ? getChartRenderState(result) : { status: "no-data" as const, model: null };
  const showChart = chartState.status === "supported";

  return (
    <OpenSection divider="top" spacing={1.65}>
      <Stack
        spacing={1.85}
        sx={{
          pl: { xs: 1.15, md: 1.45 },
          borderLeft: `2px solid ${accent}`,
          py: 0.35,
        }}
      >
        <Stack spacing={1.1}>
          <Typography variant="overline" sx={{ color: accent }}>
            {insight.type.replace(/_/g, " ")}
          </Typography>
          <Typography variant="h5">{insight.title}</Typography>
          <Typography color="text.secondary">{insight.summary}</Typography>
        </Stack>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ rowGap: 1 }}>
          <Chip
            size="small"
            color={severityTone(insight.severity)}
            label={insight.severity}
            sx={
              insight.severity === "info"
                ? {
                    backgroundColor: tokens.color.status.infoBg,
                    color: tokens.color.status.infoFg,
                  }
                : undefined
            }
          />
          <Chip size="small" variant="outlined" label={`Priority ${insight.priority}`} />
          {insight.metric ? <Chip size="small" variant="outlined" label={`Metric ${insight.metric}`} /> : null}
          {insight.dimension ? <Chip size="small" variant="outlined" label={`Dimension ${insight.dimension}`} /> : null}
          {insight.value !== null ? <Chip size="small" variant="outlined" label={`Value ${String(insight.value)}`} /> : null}
          <Chip size="small" variant="outlined" label={`Confidence ${Math.round(insight.confidence * 100)}%`} />
          <Chip size="small" variant="outlined" label={`Impact ${Math.round(insight.impact * 100)}%`} />
        </Stack>

        {onSave ? (
          <Stack direction="row">
            <Button size="small" variant="outlined" onClick={onSave}>
              Save to dashboard
            </Button>
          </Stack>
        ) : null}

        {showChart ? <AIResultChart result={result} /> : null}
        {hasRows ? <AIResultTable columns={result.columns} rows={result.rows} title="Supporting result" maxHeight={220} compact={showChart} /> : null}

        {insight.sql ? (
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
                backgroundColor: "transparent",
                "&::before": { display: "none" },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 0, px: 0, py: 0.15 }}>
                <Typography variant="subtitle2">View supporting SQL</Typography>
              </AccordionSummary>
            <AccordionDetails sx={{ px: 0, pt: 0 }}>
              <Typography
                component="pre"
                sx={{
                  m: 0,
                  fontFamily: "Monaco, Consolas, 'Courier New', monospace",
                  fontSize: 13,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  color: tokens.color.fg.primary,
                }}
              >
                {insight.sql}
              </Typography>
            </AccordionDetails>
          </Accordion>
            ) : null}
      </Stack>
    </OpenSection>
  );
}
