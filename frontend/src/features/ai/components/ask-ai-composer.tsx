import { Alert, Box, Button, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "@next/core/api/errors";
import { SurfaceCard } from "@next/components/ui/surface-card";
import { SaveToDashboardDialog } from "@next/features/dashboards/components/save-to-dashboard-dialog";
import type { CreateDashboardWidgetPayload } from "@next/features/dashboards/types";
import { tokens } from "@next/theme/tokens";

import { buildVisualizationConfig, type AIQueryResponse } from "../types";
import {
  getMutationErrorMessage,
  useAIQueryHistory,
  useAIQueryHistoryDetail,
  useAskAIMutation,
  useDeleteAIQueryHistoryMutation,
  useUpdateAIQueryHistoryMutation,
} from "../hooks";
import { AIResultView } from "./ai-result-view";
import { QueryHistoryPanel } from "./query-history-panel";

export function AskAIComposer({ datasetId }: { datasetId: number }) {
  const [question, setQuestion] = useState("");
  const [selectedQueryId, setSelectedQueryId] = useState<number | null>(null);
  const [activeResult, setActiveResult] = useState<AIQueryResponse | null>(null);
  const [activeQuestion, setActiveQuestion] = useState("");
  const [panelError, setPanelError] = useState<string | null>(null);
  const [dashboardPayload, setDashboardPayload] = useState<CreateDashboardWidgetPayload | null>(null);

  const historyQuery = useAIQueryHistory(datasetId);
  const detailQuery = useAIQueryHistoryDetail(selectedQueryId);
  const askMutation = useAskAIMutation(datasetId);
  const updateHistoryMutation = useUpdateAIQueryHistoryMutation(datasetId);
  const deleteHistoryMutation = useDeleteAIQueryHistoryMutation(datasetId);

  useEffect(() => {
    setQuestion("");
    setSelectedQueryId(null);
    setActiveResult(null);
    setActiveQuestion("");
    setPanelError(null);
  }, [datasetId]);

  useEffect(() => {
    const entries = historyQuery.data ?? [];
    if (!entries.length) {
      setSelectedQueryId(null);
      return;
    }

    if (!selectedQueryId || !entries.some((entry) => entry.id === selectedQueryId)) {
      setSelectedQueryId(entries[0].id);
    }
  }, [historyQuery.data, selectedQueryId]);

  useEffect(() => {
    if (!detailQuery.data) {
      return;
    }

    setQuestion(detailQuery.data.question);
    setActiveQuestion(detailQuery.data.question);
    setActiveResult(detailQuery.data.result);
  }, [detailQuery.data]);

  const isWorking = askMutation.isPending || detailQuery.isLoading;

  const currentTitle = useMemo(() => {
    if (activeQuestion.trim()) {
      return activeQuestion.trim();
    }
    return "Saved query widget";
  }, [activeQuestion]);

  async function handleSubmit() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    setPanelError(null);

    try {
      const response = await askMutation.mutateAsync(trimmedQuestion);
      setActiveQuestion(trimmedQuestion);
      setActiveResult(response);
      if (response.query_id) {
        setSelectedQueryId(response.query_id);
      }
    } catch (error) {
      setPanelError(getMutationErrorMessage(error, "Could not query the dataset with AI"));
    }
  }

  return (
    <Box
      sx={{
        display: "grid",
        gap: 3,
        gridTemplateColumns: {
          xs: "1fr",
          lg: "320px minmax(0, 1fr)",
        },
        alignItems: "start",
      }}
    >
      <QueryHistoryPanel
        entries={historyQuery.data ?? []}
        selectedQueryId={selectedQueryId}
        isLoading={historyQuery.isLoading}
        error={historyQuery.isError ? getApiErrorMessage(historyQuery.error, "Could not load query history") : null}
        onSelect={(queryId) => {
          setPanelError(null);
          setSelectedQueryId(queryId);
        }}
        onToggleFavorite={async (entry) => {
          await updateHistoryMutation.mutateAsync({
            queryId: entry.id,
            payload: { is_favorite: !entry.is_favorite },
          });
        }}
        onRename={async (entry, title) => {
          await updateHistoryMutation.mutateAsync({
            queryId: entry.id,
            payload: { title },
          });
        }}
        onDelete={async (entry) => {
          await deleteHistoryMutation.mutateAsync(entry.id);
          if (selectedQueryId === entry.id) {
            setActiveResult(null);
            setActiveQuestion("");
            setQuestion("");
            setSelectedQueryId(null);
          }
        }}
      />

      <Stack spacing={2.5} sx={{ minWidth: 0 }}>
        <Stack
          spacing={2}
          sx={{
            pb: 2,
            borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
          }}
        >
          <Stack spacing={2}>
            <Stack spacing={0.75}>
              <Typography variant="overline" color="text.secondary">
                Ask AI
              </Typography>
              <Typography variant="h5">Analysis composer</Typography>
              <Typography color="text.secondary">
                Ask a question, inspect generated SQL, and reopen previous answers from the rail without leaving the dataset workspace.
              </Typography>
            </Stack>

            <TextField
              label="Question"
              placeholder="Example: What are the top 10 products by revenue?"
              multiline
              minRows={3}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              disabled={askMutation.isPending}
              fullWidth
            />

            <Stack direction="row" spacing={1.25} alignItems="center" flexWrap="wrap" useFlexGap>
              <Button variant="contained" onClick={handleSubmit} disabled={askMutation.isPending || !question.trim()}>
                Ask AI
              </Button>
              <Button variant="outlined" onClick={handleSubmit} disabled={askMutation.isPending || !question.trim()}>
                Re-run
              </Button>
              {isWorking ? <CircularProgress size={22} /> : null}
            </Stack>

            {panelError ? <Alert severity="error">{panelError}</Alert> : null}
          </Stack>
        </Stack>

        {activeResult ? (
          <AIResultView
            result={activeResult}
            onSaveWidget={
              activeResult.query_id
                ? (widgetType) =>
                    setDashboardPayload({
                      type: widgetType,
                      widget_type: widgetType,
                      source_type: "query",
                      source_id: activeResult.query_id!,
                      execution_type: "query",
                      chart_type:
                        widgetType === "chart" &&
                        activeResult.visualization_suggestion?.type &&
                        activeResult.visualization_suggestion.type !== "table_only"
                          ? activeResult.visualization_suggestion.type
                          : "table",
                      query_sql: activeResult.sql,
                      config_json: buildVisualizationConfig(activeResult.visualization_suggestion),
                      data_json: activeResult.rows,
                      layout: {
                        column_span: widgetType === "chart" ? 2 : 1,
                        order: 0,
                        use_snapshot: false,
                        x: 0,
                        y: 0,
                        width: widgetType === "chart" ? 12 : 6,
                        height: widgetType === "chart" ? 6 : 4,
                      },
                      title: currentTitle,
                      save_snapshot: true,
                    })
                : undefined
            }
          />
        ) : (
          <SurfaceCard tone="quiet" padding="sm">
            <Stack spacing={0.75}>
              <Typography variant="h6">Start with a question</Typography>
              <Typography color="text.secondary">
                Select a previous query from the rail or ask a new question to start building analysis history for this dataset.
              </Typography>
            </Stack>
          </SurfaceCard>
        )}

        <SaveToDashboardDialog
          open={dashboardPayload !== null}
          title="Save query widget to dashboard"
          payload={dashboardPayload}
          datasetId={datasetId}
          defaultDashboardName="AI analysis"
          onClose={() => setDashboardPayload(null)}
        />
      </Stack>
    </Box>
  );
}
