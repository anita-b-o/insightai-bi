import { Alert, Button, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { getApiErrorMessage } from "@next/core/api/errors";
import { PageHeader } from "@next/components/ui/page-header";
import { PageSurface } from "@next/components/ui/page-surface";
import { EmptyState, ErrorState, LoadingState } from "@next/components/ui/states";
import { SectionBand } from "@next/components/ui/surface-card";
import { DashboardList } from "@next/features/dashboards/components/dashboard-list";
import { DashboardToolbar } from "@next/features/dashboards/components/dashboard-toolbar";
import { useCreateDashboard, useDashboardsList } from "@next/features/dashboards/hooks";

export function NextDashboardsPage() {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const dashboardsQuery = useDashboardsList();
  const createDashboardMutation = useCreateDashboard();

  async function handleCreate() {
    try {
      setError(null);
      const detail = await createDashboardMutation.mutateAsync({ name: name.trim() || "New dashboard" });
      setName("");
      window.location.assign(`/dashboards/${detail.id}`);
    } catch (createError: unknown) {
      setError(getApiErrorMessage(createError, "Could not create dashboard"));
    }
  }

  return (
    <PageSurface variant="workspace">
      <Stack spacing={3.5}>
        <PageHeader
          eyebrow="Reusable analysis"
          title="Dashboards"
          description="Keep high-signal AI answers and insight outputs in a persistent BI workspace."
        />

        <Stack spacing={1.15} sx={{ pb: 1.5, borderBottom: (theme) => `1px solid ${theme.palette.divider}` }}>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 820 }}>
            Create a dashboard, then keep refreshing widgets from the same backend-powered Ask AI and insight flows already in the product.
          </Typography>
          <DashboardToolbar name={name} onNameChange={setName} onCreate={() => void handleCreate()} isCreating={createDashboardMutation.isPending} />
        </Stack>

        {error ? <Alert severity="error">{error}</Alert> : null}

        {dashboardsQuery.isLoading ? <LoadingState title="Loading dashboards" description="Reading saved dashboards and widget freshness." /> : null}

        {dashboardsQuery.isError ? (
          <ErrorState
            description="Could not load dashboards."
            onRetry={() => {
              void dashboardsQuery.refetch();
            }}
          />
        ) : null}

        {dashboardsQuery.isSuccess && dashboardsQuery.data.length === 0 ? (
          <EmptyState
            title="No dashboards yet"
            description="Create one now or save Ask AI and insight outputs into a dashboard from any dataset workspace."
            action={
              <Button variant="contained" onClick={() => void handleCreate()} disabled={createDashboardMutation.isPending}>
                Create first dashboard
              </Button>
            }
          />
        ) : null}

        {dashboardsQuery.isSuccess && dashboardsQuery.data.length > 0 ? (
          <SectionBand
            eyebrow="Saved dashboards"
            title="Your reporting surfaces"
            description="Open a dashboard to inspect widget freshness, refresh individual results, and review the narrative generated from current widget outputs."
          >
            <DashboardList dashboards={dashboardsQuery.data} />
          </SectionBand>
        ) : null}
      </Stack>
    </PageSurface>
  );
}
