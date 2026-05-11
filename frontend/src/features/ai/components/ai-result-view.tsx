import type { ReactNode } from "react";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import { Accordion, AccordionDetails, AccordionSummary, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { SurfaceCard } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import type { AIQueryResponse } from "../types";
import { AIResultChart, EmptyChartState, getChartRenderState } from "./ai-result-chart";
import { AIResultTable } from "./ai-result-table";

export function AIResultView({
  result,
  onSaveWidget,
}: {
  result: AIQueryResponse;
  onSaveWidget?: (widgetType: "chart" | "table") => void;
}) {
  const metadata = result.metadata;
  const sqlAnalysis = result.sql_analysis;
  const aggregationLabel = sqlAnalysis?.is_aggregated ? "Aggregated result" : "Raw rows";
  const hasTable = result.rows.length > 0 && result.columns.length > 0;
  const chartState = getChartRenderState(result);
  const canRenderChart = chartState.status === "supported";

  return (
    <SurfaceCard tone="quiet" padding="sm">
      <Stack spacing={2.5}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {metadata?.model ? <Chip label={`Model: ${metadata.model}`} variant="outlined" /> : null}
          {metadata ? (
            <Chip
              label={metadata.fallback_used ? "Fallback used" : "Direct SQL answer"}
              sx={{
                backgroundColor: metadata.fallback_used ? tokens.color.status.warningBg : tokens.color.status.successBg,
                color: metadata.fallback_used ? tokens.color.status.warningFg : tokens.color.status.successFg,
              }}
            />
          ) : null}
          {metadata ? (
            <Chip
              label={metadata.cache_hit ? "Cache hit" : "Fresh result"}
              sx={{
                backgroundColor: metadata.cache_hit ? tokens.color.status.infoBg : tokens.color.bg.surface,
                color: metadata.cache_hit ? tokens.color.status.infoFg : tokens.color.fg.secondary,
              }}
            />
          ) : null}
          {sqlAnalysis ? (
            <Chip label={aggregationLabel} variant="outlined" />
          ) : null}
        </Stack>

        <ResultSection title="Answer" accent={tokens.color.accent.blue}>
          <Typography variant="body1">{result.answer}</Typography>
        </ResultSection>

        {onSaveWidget ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {canRenderChart ? (
              <Button size="small" variant="outlined" onClick={() => onSaveWidget("chart")}>
                Save chart to dashboard
              </Button>
            ) : null}
            <Button size="small" variant="outlined" onClick={() => onSaveWidget("table")}>
              Save table to dashboard
            </Button>
          </Stack>
        ) : null}

        {hasTable ? (
          canRenderChart ? (
            <AIResultChart result={result} />
          ) : (
            <EmptyChartState />
          )
        ) : null}

        {hasTable ? <AIResultTable columns={result.columns} rows={result.rows} maxHeight={300} title="Supporting result" /> : null}

        {result.sql ? (
          <ResultSection title="Query details" accent={tokens.color.accent.cyan}>
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                border: `1px solid ${alpha(tokens.color.border.strong, 0.36)}`,
                borderRadius: `${tokens.radius.xs}px !important`,
                backgroundColor: tokens.color.bg.surface,
                "&::before": { display: "none" },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 0, px: 1.5, py: 0.2 }}>
                <Typography variant="subtitle2">View generated SQL</Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ pt: 0, px: 1.5, pb: 1.35 }}>
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
                  {result.sql}
                </Typography>
              </AccordionDetails>
            </Accordion>
          </ResultSection>
        ) : null}

        {result.chart_suggestion ? (
          <ResultSection title="Backend chart hint" accent={tokens.color.accent.plum}>
            <Typography variant="body2" color="text.secondary">
              {result.chart_suggestion.type}
              {result.chart_suggestion.explanation ? ` — ${result.chart_suggestion.explanation}` : ""}
            </Typography>
          </ResultSection>
        ) : null}
      </Stack>
    </SurfaceCard>
  );
}

function ResultSection({ title, children, accent }: { title: string; children: ReactNode; accent: string }) {
  return (
    <Stack
      spacing={1}
      sx={{
        pt: 1.35,
        borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          top: -1,
          left: 0,
          width: 44,
          height: 2,
          bgcolor: accent,
        },
      }}
    >
      <Typography variant="h6">{title}</Typography>
      {children}
    </Stack>
  );
}
