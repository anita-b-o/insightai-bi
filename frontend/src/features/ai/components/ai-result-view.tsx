import type { ReactNode } from "react";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import { Accordion, AccordionDetails, AccordionSummary, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { OpenSection, SectionBlock } from "@next/components/ui/surface-card";
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
    <Stack spacing={2.15}>
      <OpenSection divider="top" spacing={1.2}>
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
      </OpenSection>

      <ResultSection title="Answer">
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
          <SectionBlock divider="top">
            <AIResultChart result={result} />
          </SectionBlock>
        ) : (
          <SectionBlock divider="top">
            <EmptyChartState />
          </SectionBlock>
        )
      ) : null}

      {hasTable ? (
        <SectionBlock divider="top">
          <AIResultTable columns={result.columns} rows={result.rows} maxHeight={300} title="Supporting result" />
        </SectionBlock>
      ) : null}

      {result.sql ? (
        <ResultSection title="Query details">
          <Accordion
            disableGutters
            elevation={0}
            sx={{
              borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.28)}`,
              borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.28)}`,
              borderRadius: 0,
              backgroundColor: "transparent",
              "&::before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreRoundedIcon />} sx={{ minHeight: 0, px: 0.2, py: 0.2 }}>
              <Typography variant="subtitle2">View generated SQL</Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0, px: 0.2, pb: 1.1 }}>
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
        <ResultSection title="Backend chart hint">
          <Typography variant="body2" color="text.secondary">
            {result.chart_suggestion.type}
            {result.chart_suggestion.explanation ? ` — ${result.chart_suggestion.explanation}` : ""}
          </Typography>
        </ResultSection>
      ) : null}
    </Stack>
  );
}

function ResultSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Stack
      spacing={1}
      sx={{
        pt: 1.35,
        borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
      }}
    >
      <Typography variant="h6">{title}</Typography>
      {children}
    </Stack>
  );
}
