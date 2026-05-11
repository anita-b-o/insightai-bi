import { alpha } from "@mui/material/styles";
import { Box, Button, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { StatusBadge } from "@next/components/ui/status-badge";
import { MetricStrip, MetricStripItem, SurfaceCard } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import type { DatasetSummaryDto } from "./api";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

function formatCount(value: number) {
  return value.toLocaleString();
}

function formatFileLabel(filename: string) {
  const parts = filename.split(".");
  const extension = parts.length > 1 ? parts.pop()?.toUpperCase() : null;
  return extension ? `${extension} source` : "Uploaded source";
}

export function WorkspaceMetricsRow({
  datasets,
}: {
  datasets: DatasetSummaryDto[];
}) {
  const primaryDataset = datasets[0];
  const totalRows = datasets.reduce((sum, dataset) => sum + dataset.row_count, 0);

  return (
    <MetricStrip accent>
      <MetricStripItem label="Datasets" value={datasets.length.toLocaleString()} detail="Available sources in this workspace" />
      <MetricStripItem
        label="Rows available"
        value={formatCount(totalRows)}
        detail="Current profiling volume across uploaded CSVs"
      />
      <MetricStripItem
        label="Latest import"
        value={formatDate(primaryDataset.created_at)}
        detail={primaryDataset.name}
      />
    </MetricStrip>
  );
}

export function PrimaryDatasetHero({ dataset }: { dataset: DatasetSummaryDto }) {
  return (
    <Box
      sx={{
        borderRadius: tokens.radius.md,
        border: `1px solid ${alpha(tokens.color.border.strong, 0.5)}`,
        backgroundColor: alpha(tokens.color.bg.surface, 0.86),
        borderLeft: `3px solid ${tokens.color.accent.blue}`,
        p: { xs: 1.7, md: 2 },
        display: "grid",
        gap: 1.75,
      }}
    >
      <Stack direction={{ xs: "column", lg: "row" }} spacing={1.6} justifyContent="space-between" alignItems={{ xs: "flex-start", lg: "flex-start" }}>
        <Stack spacing={0.9} sx={{ maxWidth: 760 }}>
          <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
            Primary dataset
          </Typography>
          <Typography variant="h4" sx={{ maxWidth: 680 }}>
            {dataset.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 700 }}>
            {dataset.description || "Ready for schema inspection, Ask AI exploration, and dashboard-ready insight generation."}
          </Typography>
        </Stack>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button component={RouterLink} to={`/datasets/${dataset.id}`} variant="contained">
            Open dataset
          </Button>
          <Button component={RouterLink} to="/upload" variant="outlined">
            Upload another
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <StatusBadge label={`${dataset.column_count} columns`} tone="info" />
        <StatusBadge label={`${formatCount(dataset.row_count)} rows`} tone="success" />
        <StatusBadge label={formatFileLabel(dataset.original_filename)} tone="warning" />
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" },
          gap: 1.25,
        }}
      >
        <HeroStat label="Imported" value={formatDateTime(dataset.created_at)} />
        <HeroStat label="Source file" value={dataset.original_filename} />
        <HeroStat label="Next step" value="Inspect schema and launch Ask AI" />
      </Box>
    </Box>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <Stack
      spacing={0.5}
      sx={{
        minWidth: 0,
        p: 0,
        borderRadius: 0,
        border: "none",
        borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
        backgroundColor: "transparent",
        pt: 1.1,
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {value}
      </Typography>
    </Stack>
  );
}

export function DatasetListSection({ datasets }: { datasets: DatasetSummaryDto[] }) {
  if (datasets.length === 0) {
    return null;
  }

  return (
    <Stack spacing={0}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "flex-end" }}
        sx={{ pb: 1.5 }}
      >
        <Stack spacing={0.5}>
          <Typography variant="overline" color="text.secondary">
            Dataset collection
          </Typography>
          <Typography variant="h5">Other datasets in this workspace</Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Compact list for quick re-entry and schema review.
        </Typography>
      </Stack>

      <Box sx={{ borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.5)}` }}>
        {datasets.map((dataset) => (
          <DatasetListItem key={dataset.id} dataset={dataset} />
        ))}
      </Box>
    </Stack>
  );
}

function DatasetListItem({ dataset }: { dataset: DatasetSummaryDto }) {
  return (
    <Box
      sx={{
        py: 1.75,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.38)}`,
      }}
    >
      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", lg: "center" }}
      >
        <Stack spacing={0.75} sx={{ minWidth: 0 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ xs: "flex-start", sm: "center" }}>
            <Typography variant="h6">{dataset.name}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
              {formatFileLabel(dataset.original_filename)}
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {dataset.description || "No description provided yet."}
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <Typography variant="body2" color="text.secondary">
              {formatCount(dataset.row_count)} rows
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {dataset.column_count} columns
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Imported {formatDateTime(dataset.created_at)}
            </Typography>
          </Stack>
        </Stack>

        <Button component={RouterLink} to={`/datasets/${dataset.id}`} variant="text" sx={{ flexShrink: 0 }}>
          Open dataset
        </Button>
      </Stack>
    </Box>
  );
}

export function QuickActionsRail() {
  return (
    <SurfaceCard tone="panel" padding="md">
      <Stack spacing={1.9}>
        <Stack spacing={0.75}>
          <Typography variant="overline" sx={{ color: tokens.color.accent.blue }}>
            Quick actions
          </Typography>
          <Typography variant="h6">Keep the workflow moving</Typography>
          <Typography variant="body2" color="text.secondary">
            Add another CSV, open the demo, or continue into schema inspection and AI-assisted analysis.
          </Typography>
        </Stack>

        <Stack spacing={0.9}>
          <Button component={RouterLink} to="/upload" variant="contained" fullWidth>
            Upload dataset
          </Button>
          <Button component={RouterLink} to="/demo" variant="outlined" fullWidth>
            Try demo
          </Button>
        </Stack>

        <Box
          sx={{
            borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.36)}`,
            pt: 1.25,
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Suggested flow
          </Typography>
          <Stack component="ol" spacing={0.72} sx={{ mb: 0, mt: 0.9, pl: 2.1 }}>
            <Typography component="li" variant="body2" color="text.secondary">
              Upload or select a dataset
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Inspect schema and sample values
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Ask AI, review insights, and save widgets
            </Typography>
          </Stack>
        </Box>
      </Stack>
    </SurfaceCard>
  );
}
