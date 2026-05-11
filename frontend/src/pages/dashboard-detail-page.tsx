import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import { alpha } from "@mui/material/styles";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useRef, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import { getApiErrorMessage } from "@next/core/api/errors";
import { PageHeader } from "@next/components/ui/page-header";
import { PageSurface } from "@next/components/ui/page-surface";
import { StatusBadge } from "@next/components/ui/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@next/components/ui/states";
import { MetricStrip, MetricStripItem, SectionBand, SurfaceCard } from "@next/components/ui/surface-card";
import { DashboardGrid } from "@next/features/dashboards/components/dashboard-grid";
import { ExportDashboardButton } from "@next/features/dashboards/components/export-dashboard-button";
import { ShareDialog } from "@next/features/dashboards/components/share-dialog";
import { DashboardToolbar } from "@next/features/dashboards/components/dashboard-toolbar";
import { DashboardWidget } from "@next/features/dashboards/components/dashboard-widget";
import { useDashboardDetail, useDashboardNarrative, useRefreshDashboard, useRefreshDashboardWidget } from "@next/features/dashboards/hooks";
import {
  dashboardFreshnessTone,
  formatDashboardDateTime,
  formatDashboardInterval,
  formatFreshnessLabel,
} from "@next/features/dashboards/types";
import { tokens } from "@next/theme/tokens";

function NarrativeStrip({
  summary,
  findings,
  caveats,
}: {
  summary: string;
  findings: string[];
  caveats: string[];
}) {
  if (!summary && findings.length === 0 && caveats.length === 0) {
    return null;
  }

  return (
    <SurfaceCard tone="quiet" padding="sm">
      <Stack spacing={1.6} sx={{ py: 1.15, borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.45)}` }}>
        {summary ? (
          <Typography variant="body1" sx={{ maxWidth: 980 }}>
            {summary}
          </Typography>
        ) : null}
        {findings.length > 0 ? (
          <Stack spacing={0.8}>
            <Typography variant="overline" color="text.secondary">
              Key findings
            </Typography>
            {findings.slice(0, 3).map((item) => (
              <Typography key={item} variant="body2" color="text.secondary">
                {item}
              </Typography>
            ))}
          </Stack>
        ) : null}
        {caveats.length > 0 ? (
          <Typography variant="body2" color="text.secondary">
            Caveat: {caveats[0]}
          </Typography>
        ) : null}
      </Stack>
    </SurfaceCard>
  );
}

export function NextDashboardDetailPage() {
  const { dashboardId } = useParams();
  const parsedDashboardId = dashboardId ? Number(dashboardId) : null;
  const detailQuery = useDashboardDetail(parsedDashboardId);
  const narrativeQuery = useDashboardNarrative(parsedDashboardId);
  const refreshDashboardMutation = useRefreshDashboard(parsedDashboardId ?? 0);
  const refreshWidgetMutation = useRefreshDashboardWidget(parsedDashboardId ?? 0);
  const [widgetErrors, setWidgetErrors] = useState<Record<number, string | null>>({});
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const widgetsContainerRef = useRef<HTMLDivElement | null>(null);

  if (!dashboardId || parsedDashboardId === null || Number.isNaN(parsedDashboardId)) {
    return (
      <PageSurface variant="workspace">
        <EmptyState
          title="Dashboard not found"
          description="This route is missing a valid dashboard identifier."
          action={
            <Button component={RouterLink} to="/dashboards" variant="contained">
              Back to dashboards
            </Button>
          }
        />
      </PageSurface>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <PageSurface variant="workspace">
        <LoadingState title="Loading dashboard" description="Fetching widget layout, freshness, and narrative." />
      </PageSurface>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <PageSurface variant="workspace">
        <ErrorState
          description="Could not load dashboard."
          onRetry={() => {
            void detailQuery.refetch();
          }}
        />
      </PageSurface>
    );
  }

  const dashboard = detailQuery.data;

  async function handleRefreshDashboard() {
    try {
      await refreshDashboardMutation.mutateAsync();
      setWidgetErrors({});
      await narrativeQuery.refetch();
    } catch {
      // surfaced by query state below
    }
  }

  async function handleRefreshWidget(widgetId: number) {
    try {
      setWidgetErrors((current) => ({ ...current, [widgetId]: null }));
      await refreshWidgetMutation.mutateAsync(widgetId);
      await narrativeQuery.refetch();
    } catch (error: unknown) {
      setWidgetErrors((current) => ({
        ...current,
        [widgetId]: getApiErrorMessage(error, "Could not refresh widget"),
      }));
    }
  }

  return (
    <PageSurface variant="workspace">
      <Stack spacing={3}>
        <PageHeader
          eyebrow="Dashboard workspace"
          title={dashboard.name}
          description="Review saved widgets, refresh result snapshots from the backend, and inspect the current dashboard narrative."
          action={
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
              <Button component={RouterLink} to="/dashboards" variant="outlined">
                All dashboards
              </Button>
              <Button variant="contained" startIcon={<RefreshRoundedIcon />} onClick={() => void handleRefreshDashboard()} disabled={refreshDashboardMutation.isPending}>
                {refreshDashboardMutation.isPending ? "Refreshing..." : "Refresh dashboard"}
              </Button>
            </Stack>
          }
        />

        <Box
          sx={{
            borderRadius: tokens.radius.md,
            border: `1px solid ${alpha(tokens.color.border.strong, 0.5)}`,
            borderLeft: `3px solid ${tokens.color.accent.blue}`,
            backgroundColor: tokens.color.bg.surface,
            overflow: "hidden",
          }}
        >
          <Stack spacing={2.15} sx={{ p: { xs: 1.55, md: 1.8 } }}>
            <Stack direction={{ xs: "column", lg: "row" }} spacing={1.5} justifyContent="space-between" alignItems={{ xs: "flex-start", lg: "center" }}>
              <Stack spacing={0.85}>
                <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                  <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
                    Active dashboard
                  </Typography>
                  <StatusBadge label={formatFreshnessLabel(dashboard.freshness_status)} tone={dashboardFreshnessTone(dashboard.freshness_status)} />
                </Stack>
                <Typography variant="body2" color="text.secondary">
                  {dashboard.widgets.length} widgets • Updated {formatDashboardDateTime(dashboard.updated_at)}
                </Typography>
              </Stack>

              <DashboardToolbar
                detailActions={
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                    <Button variant="outlined" onClick={() => setIsShareDialogOpen(true)}>
                      Share
                    </Button>
                    <ExportDashboardButton
                      dashboard={dashboard}
                      narrative={narrativeQuery.isSuccess ? narrativeQuery.data : null}
                      widgetsContainer={widgetsContainerRef.current}
                    />
                  </Stack>
                }
              />
            </Stack>

            <MetricStrip desktopColumns={4} accent>
              <MetricStripItem label="Widgets" value={dashboard.widgets.length.toLocaleString()} detail="Saved on canvas" />
              <MetricStripItem label="Auto refresh" value={dashboard.auto_refresh_enabled ? "Enabled" : "Disabled"} detail={formatDashboardInterval(dashboard.refresh_interval_minutes)} />
              <MetricStripItem label="Last success" value={formatDashboardDateTime(dashboard.last_successful_refresh_at)} detail="Latest successful run" />
              <MetricStripItem label="Next refresh" value={formatDashboardDateTime(dashboard.next_refresh_at)} detail="Backend schedule" />
            </MetricStrip>
          </Stack>
        </Box>

        {refreshDashboardMutation.isError ? <Alert severity="error">{getApiErrorMessage(refreshDashboardMutation.error, "Could not refresh dashboard")}</Alert> : null}

        {narrativeQuery.isSuccess ? (
          <SectionBand
            eyebrow="Narrative"
            title="Current interpretation"
            description="This summary is generated from the present widget state returned by the backend."
            density="compact"
            divider="subtle"
          >
            <NarrativeStrip
              summary={narrativeQuery.data.summary}
              findings={narrativeQuery.data.key_findings}
              caveats={narrativeQuery.data.risks_or_caveats}
            />
          </SectionBand>
        ) : null}

        {dashboard.widgets.length === 0 ? (
          <EmptyState
            title="No widgets yet"
            description="This dashboard exists, but it does not contain saved widgets yet. Save Ask AI results or insights from a dataset workspace."
            action={
              <Button component={RouterLink} to="/datasets" variant="contained">
                Go to datasets
              </Button>
            }
          />
        ) : (
          <SectionBand
            eyebrow="Canvas"
            title="Saved widgets"
            description="Widgets stay lighter visually here while the grid remains the main surface. Refresh any single widget without leaving the canvas."
            density="compact"
            divider="none"
          >
            <Box ref={widgetsContainerRef}>
              <DashboardGrid
                widgets={dashboard.widgets}
                renderWidget={(widget) => (
                  <DashboardWidget
                    widget={widget}
                    isBusy={refreshWidgetMutation.isPending && refreshWidgetMutation.variables === widget.id}
                    error={widgetErrors[widget.id] ?? null}
                    onRefresh={() => void handleRefreshWidget(widget.id)}
                  />
                )}
              />
            </Box>
          </SectionBand>
        )}
      </Stack>

      <ShareDialog
        dashboardId={dashboard.id}
        dashboardName={dashboard.name}
        open={isShareDialogOpen}
        onClose={() => setIsShareDialogOpen(false)}
      />
    </PageSurface>
  );
}
