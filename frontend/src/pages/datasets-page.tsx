import { Button, Stack } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@next/components/ui/states";
import { PageSurface } from "@next/components/ui/page-surface";
import { PageHeader } from "@next/components/ui/page-header";
import { useDatasetsList } from "@next/features/datasets/hooks";
import { DatasetListSection, PrimaryDatasetHero, QuickActionsRail, WorkspaceMetricsRow } from "@next/features/datasets/workspace";

export function NextDatasetsPage() {
  const datasetsQuery = useDatasetsList();
  const datasets = datasetsQuery.data
    ? [...datasetsQuery.data].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    : [];
  const primaryDataset = datasets[0];
  const secondaryDatasets = datasets.slice(1);

  return (
    <PageSurface variant="workspace">
      <Stack spacing={3}>
        <PageHeader
          eyebrow="Dataset workspace"
          title="Datasets"
          description="A BI workspace for uploading CSVs, inspecting schema profiles, and moving directly into AI-assisted exploration."
          action={
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
              <Button variant="outlined" component={RouterLink} to="/demo">
                Try demo
              </Button>
              <Button variant="contained" component={RouterLink} to="/upload">
                Upload dataset
              </Button>
            </Stack>
          }
        />

        {datasetsQuery.isLoading ? <LoadingState title="Loading datasets" description="Reading your uploaded datasets." /> : null}

        {datasetsQuery.isError ? (
          <ErrorState
            description="Could not load datasets."
            onRetry={() => {
              void datasetsQuery.refetch();
            }}
          />
        ) : null}

        {datasetsQuery.isSuccess && datasetsQuery.data.length === 0 ? (
          <EmptyState
            title="No datasets yet"
            description="Upload a CSV to generate the first metadata profile and start the analytics workflow."
            action={
              <Button component={RouterLink} to="/upload" variant="contained">
                Upload CSV
              </Button>
            }
          />
        ) : null}

        {datasetsQuery.isSuccess && primaryDataset ? (
          <Stack spacing={2.15}>
            <WorkspaceMetricsRow datasets={datasets} />

            <PrimaryDatasetHero dataset={primaryDataset} />

            <Stack
              direction={{ xs: "column", xl: "row" }}
              spacing={{ xs: 2, xl: 2.1 }}
              alignItems={{ xs: "stretch", xl: "flex-start" }}
            >
              <Stack spacing={2} sx={{ flex: 1, minWidth: 0 }}>
                <DatasetListSection datasets={secondaryDatasets} />
              </Stack>

              <Stack
                sx={{
                  width: "100%",
                  maxWidth: { xl: 304 },
                  flexShrink: 0,
                  pl: { xl: 0 },
                  mt: { xl: -0.2 },
                  alignSelf: "flex-start",
                }}
              >
                <QuickActionsRail />
              </Stack>
            </Stack>
          </Stack>
        ) : null}
      </Stack>
    </PageSurface>
  );
}
