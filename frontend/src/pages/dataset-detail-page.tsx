import { alpha } from "@mui/material/styles";
import { Box, Button, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { Link as RouterLink, useParams } from "react-router-dom";

import { DataTableFrame } from "@next/components/ui/data-table";
import { PageHeader } from "@next/components/ui/page-header";
import { PageSurface } from "@next/components/ui/page-surface";
import { MetricStrip, MetricStripItem, SectionBand, SurfaceCard } from "@next/components/ui/surface-card";
import { EmptyState, ErrorState, LoadingState } from "@next/components/ui/states";
import { AskAIComposer } from "@next/features/ai/components/ask-ai-composer";
import { useDatasetDetail } from "@next/features/datasets/hooks";
import { InsightsSection } from "@next/features/insights/components/insights-section";
import { tokens } from "@next/theme/tokens";

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function WorkflowRail() {
  return (
    <SurfaceCard tone="panel" padding="md">
      <Stack spacing={2.2}>
        <Stack component="ol" spacing={1.1} sx={{ m: 0, pl: 2.25 }}>
          <Typography component="li" variant="body2" color="text.secondary">
            Review inferred columns and sample values
          </Typography>
          <Typography component="li" variant="body2" color="text.secondary">
            Ask a focused question and inspect SQL + results
          </Typography>
          <Typography component="li" variant="body2" color="text.secondary">
            Generate insights and save high-signal widgets
          </Typography>
        </Stack>

        <Button component={RouterLink} to="/dashboards" variant="outlined" fullWidth>
          Open dashboards
        </Button>
      </Stack>
    </SurfaceCard>
  );
}

export function NextDatasetDetailPage() {
  const { datasetId } = useParams();
  const parsedDatasetId = datasetId ? Number(datasetId) : null;
  const datasetQuery = useDatasetDetail(parsedDatasetId);

  if (!datasetId || parsedDatasetId === null || Number.isNaN(parsedDatasetId)) {
    return (
      <PageSurface variant="workspace">
        <EmptyState
          title="Dataset not found"
          description="This route is missing a valid dataset identifier."
          action={
            <Button component={RouterLink} to="/datasets" variant="contained">
              Back to datasets
            </Button>
          }
        />
      </PageSurface>
    );
  }

  if (datasetQuery.isLoading) {
    return (
      <PageSurface variant="workspace">
        <LoadingState title="Loading dataset" description="Fetching schema profile, AI history, and saved insight context." />
      </PageSurface>
    );
  }

  if (datasetQuery.isError || !datasetQuery.data) {
    return (
      <PageSurface variant="workspace">
        <ErrorState
          description="Could not load dataset."
          onRetry={() => {
            void datasetQuery.refetch();
          }}
        />
      </PageSurface>
    );
  }

  const dataset = datasetQuery.data;

  return (
    <PageSurface variant="workspace">
      <Stack spacing={3}>
        <PageHeader
          eyebrow="Dataset workspace"
          title={dataset.name}
          description={dataset.description || "This dataset is ready for schema review, Ask AI exploration, and automated insight generation."}
          action={
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
              <Button component={RouterLink} to="/datasets" variant="outlined">
                All datasets
              </Button>
              <Button component={RouterLink} to="/upload" variant="contained">
                Upload another
              </Button>
            </Stack>
          }
        />

        <Stack spacing={2}>
          <Box
            sx={{
              borderRadius: tokens.radius.md,
              border: `1px solid ${alpha(tokens.color.border.strong, 0.5)}`,
              borderLeft: `3px solid ${tokens.color.accent.blue}`,
              backgroundColor: tokens.color.bg.surface,
              overflow: "hidden",
            }}
          >
            <Stack spacing={0}>
              <Stack direction={{ xs: "column", xl: "row" }} spacing={1.5} justifyContent="space-between" alignItems={{ xs: "flex-start", xl: "center" }} sx={{ p: { xs: 1.55, md: 1.8 } }}>
                <Stack spacing={0.6} sx={{ maxWidth: 880 }}>
                  <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
                    Active dataset
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Source file: {dataset.original_filename}
                  </Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary">
                  Imported {new Date(dataset.created_at).toLocaleString()}
                </Typography>
              </Stack>
              <Box sx={{ px: { xs: 1.2, md: 1.45 }, borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.26)}` }}>
                <MetricStrip accent>
                  <MetricStripItem label="Rows" value={dataset.row_count.toLocaleString()} detail="Ready to query" />
                  <MetricStripItem label="Columns" value={dataset.column_count.toLocaleString()} detail="Schema fields detected" />
                  <MetricStripItem label="File size" value={formatBytes(dataset.file_size_bytes)} detail="CSV source volume" />
                </MetricStrip>
              </Box>
            </Stack>
          </Box>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.6fr) 320px" },
              gap: { xs: 2.5, lg: 2.75 },
              alignItems: "start",
            }}
          >
            <Stack spacing={tokens.spacing.blockGap / 8} sx={{ minWidth: 0 }}>
              <SectionBand
                eyebrow="Schema profile"
                title="Detected columns"
                description="Open schema table for fast scanning of field types, nullability, cardinality, and representative values."
                density="compact"
                divider="none"
              >
                <DataTableFrame maxHeight={520}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell>Nullable</TableCell>
                        <TableCell align="right">Distinct</TableCell>
                        <TableCell>Sample value</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {dataset.columns.map((column) => (
                        <TableRow key={column.id} hover>
                          <TableCell>{column.name}</TableCell>
                          <TableCell>{column.inferred_type}</TableCell>
                          <TableCell>{column.nullable ? "Yes" : "No"}</TableCell>
                          <TableCell align="right">{column.distinct_count ?? "-"}</TableCell>
                          <TableCell>{column.sample_value ?? "-"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </DataTableFrame>
              </SectionBand>
            </Stack>

            <Box
              sx={{
                minWidth: 0,
              }}
            >
              <SectionBand
                eyebrow="Workflow"
                title="Recommended next steps"
                description="Move from schema inspection into AI-assisted analysis, then save results back into dashboards."
                density="compact"
                divider="none"
              >
                <WorkflowRail />
              </SectionBand>
            </Box>
          </Box>
        </Stack>

        <SectionBand
          eyebrow="Automated analysis"
          title="Insights"
          description="Generate analyst-style findings before asking a direct question."
          density="comfortable"
          divider="subtle"
        >
          <InsightsSection datasetId={dataset.id} />
        </SectionBand>

        <SectionBand
          eyebrow="Interactive analysis"
          title="Ask AI"
          description="Open the composer, inspect generated SQL, compare answers, and keep a reusable history for this dataset."
          density="comfortable"
          divider="none"
        >
          <AskAIComposer datasetId={dataset.id} />
        </SectionBand>
      </Stack>
    </PageSurface>
  );
}
