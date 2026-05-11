import { Alert, Button, CircularProgress, Chip, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { getApiErrorMessage, toApiError } from "@next/core/api/errors";
import { SurfaceCard } from "@next/components/ui/surface-card";
import { SaveToDashboardDialog } from "@next/features/dashboards/components/save-to-dashboard-dialog";
import type { CreateDashboardWidgetPayload } from "@next/features/dashboards/types";
import { tokens } from "@next/theme/tokens";

import { buildVisualizationConfig } from "@next/features/ai/types";

import { useGenerateDatasetInsights, useLatestDatasetInsights } from "../hooks";
import type { InsightItem, InsightNarrative } from "../types";
import { InsightCard } from "./insight-card";
import { InsightEmptyState } from "./insight-empty-state";

function NarrativeBlock({ narrative }: { narrative: InsightNarrative }) {
  const hasNarrative =
    Boolean(narrative.summary.trim()) ||
    narrative.key_findings.length > 0 ||
    narrative.risks_or_caveats.length > 0 ||
    narrative.recommended_next_questions.length > 0;

  if (!hasNarrative) {
    return null;
  }

  return (
    <SurfaceCard tone="quiet" padding="sm">
      <Stack spacing={2}>
        <Stack spacing={0.75}>
          <Typography variant="overline" color="text.secondary">
            Executive summary
          </Typography>
          {narrative.summary ? <Typography color="text.secondary">{narrative.summary}</Typography> : null}
        </Stack>

        {narrative.key_findings.length > 0 ? (
          <Stack spacing={0.75}>
            <Typography variant="subtitle2">Key findings</Typography>
            <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2.5 }}>
              {narrative.key_findings.slice(0, 5).map((item) => (
                <Typography key={item} component="li" variant="body2" color="text.secondary">
                  {item}
                </Typography>
              ))}
            </Stack>
          </Stack>
        ) : null}

        {narrative.risks_or_caveats.length > 0 ? (
          <Stack spacing={0.75}>
            <Typography variant="subtitle2">Caveats</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {narrative.risks_or_caveats.slice(0, 4).map((item) => (
                <Chip key={item} size="small" variant="outlined" label={item} />
              ))}
            </Stack>
          </Stack>
        ) : null}

        {narrative.recommended_next_questions.length > 0 ? (
          <Stack spacing={0.75}>
            <Typography variant="subtitle2">Recommended next questions</Typography>
            <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2.5 }}>
              {narrative.recommended_next_questions.slice(0, 4).map((item) => (
                <Typography key={item} component="li" variant="body2" color="text.secondary">
                  {item}
                </Typography>
              ))}
            </Stack>
          </Stack>
        ) : null}
      </Stack>
    </SurfaceCard>
  );
}

export function InsightsSection({ datasetId }: { datasetId: number }) {
  const insightsQuery = useLatestDatasetInsights(datasetId);
  const generateMutation = useGenerateDatasetInsights(datasetId);
  const [dashboardPayload, setDashboardPayload] = useState<CreateDashboardWidgetPayload | null>(null);

  const response = insightsQuery.data ?? null;
  const isMissingPersistedRun = insightsQuery.error ? toApiError(insightsQuery.error).status === 404 : false;

  async function handleGenerate() {
    await generateMutation.mutateAsync(Boolean(response));
  }

  return (
    <Stack spacing={2.5}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
      >
        <Stack spacing={0.75}>
          <Typography variant="overline" color="text.secondary">
            Automated analysis
          </Typography>
          <Typography variant="h5">Insights</Typography>
          <Typography color="text.secondary">
            Generate analyst-style findings directly from the dataset before asking a specific question.
          </Typography>
        </Stack>
        <Button variant="contained" onClick={() => void handleGenerate()} disabled={generateMutation.isPending}>
          {response ? "Refresh insights" : "Generate insights"}
        </Button>
      </Stack>

      {insightsQuery.isLoading ? (
        <Stack direction="row" spacing={1.25} alignItems="center">
          <CircularProgress size={22} />
          <Typography color="text.secondary">Loading latest persisted insights...</Typography>
        </Stack>
      ) : null}

      {generateMutation.isPending ? (
        <Stack direction="row" spacing={1.25} alignItems="center">
          <CircularProgress size={22} />
          <Typography color="text.secondary">Generating insights...</Typography>
        </Stack>
      ) : null}

      {insightsQuery.isError && !isMissingPersistedRun ? (
        <Alert severity="error">{getApiErrorMessage(insightsQuery.error, "Could not load insights")}</Alert>
      ) : null}

      {generateMutation.isError ? (
        <Alert severity="error">{getApiErrorMessage(generateMutation.error, "Could not generate insights")}</Alert>
      ) : null}

      {response ? (
        <Stack spacing={2.25}>
          <Typography variant="caption" color="text.secondary">
            Generated {new Date(response.generated_at).toLocaleString()}
          </Typography>
          {response.is_stale ? <Alert severity="warning">Dataset changed since these insights were generated.</Alert> : null}

          <NarrativeBlock narrative={response.narrative} />

          <Stack spacing={2.5}>
            {response.insights.map((insight, index) => (
              <InsightCard
                key={insight.id || `${insight.type}-${index}`}
                insight={insight}
                onSave={
                  response.run_id
                    ? () =>
                        setDashboardPayload({
                          type: "insight",
                          widget_type: "insight",
                          source_type: "insight",
                          source_id: response.run_id!,
                          execution_type: "insight",
                          chart_type: insight.chart_type,
                          query_sql: insight.sql,
                          config_json: buildVisualizationConfig(insight.visualization_suggestion),
                          data_json: insight.data?.length ? insight.data : insight.rows,
                          layout: {
                            column_span: 1,
                            order: index,
                            use_snapshot: false,
                            x: 0,
                            y: index * 4,
                            width: 6,
                            height: 5,
                          },
                          title: insight.title,
                          insight_index: index,
                          save_snapshot: true,
                        })
                    : undefined
                }
              />
            ))}
          </Stack>
        </Stack>
      ) : null}

      {!response && !insightsQuery.isLoading && !generateMutation.isPending && (isMissingPersistedRun || !insightsQuery.isError) ? (
        <InsightEmptyState isGenerating={generateMutation.isPending} onGenerate={() => void handleGenerate()} />
      ) : null}

      <SaveToDashboardDialog
        open={dashboardPayload !== null}
        title="Save insight to dashboard"
        payload={dashboardPayload}
        datasetId={datasetId}
        defaultDashboardName="Dataset insights"
        onClose={() => setDashboardPayload(null)}
      />
    </Stack>
  );
}
