import { Alert, Button, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useParams } from "react-router-dom";

import { PageHeader } from "@next/components/ui/page-header";
import { PageSurface } from "@next/components/ui/page-surface";
import { StatusBadge } from "@next/components/ui/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@next/components/ui/states";
import { MetricStrip, MetricStripItem, SectionBand, SurfaceCard } from "@next/components/ui/surface-card";
import { DashboardGrid } from "@next/features/dashboards/components/dashboard-grid";
import { DashboardWidget } from "@next/features/dashboards/components/dashboard-widget";
import { dashboardFreshnessTone, formatDashboardDateTime, formatFreshnessLabel } from "@next/features/dashboards/types";
import { useSharedDashboard } from "@next/features/share/hooks";
import { tokens } from "@next/theme/tokens";

function PublicNarrative({
  summary,
  findings,
  caveats,
}: {
  summary: string;
  findings: string[];
  caveats: string[];
}) {
  return (
    <SurfaceCard tone="quiet" padding="sm">
      <Stack spacing={1.6} sx={{ py: 1.15, borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.45)}` }}>
        <Typography variant="body1" sx={{ maxWidth: 980 }}>
          {summary || "No narrative summary available for this shared dashboard."}
        </Typography>
        {findings.length > 0 ? (
          <Stack spacing={0.8}>
            <Typography variant="overline" color="text.secondary">
              Key findings
            </Typography>
            {findings.slice(0, 4).map((item) => (
              <Typography key={item} variant="body2" color="text.secondary">
                {item}
              </Typography>
            ))}
          </Stack>
        ) : null}
        {caveats.length > 0 ? <Alert severity="warning">{caveats[0]}</Alert> : null}
      </Stack>
    </SurfaceCard>
  );
}

export function NextSharedDashboardPage() {
  const { token } = useParams();
  const sharedDashboardQuery = useSharedDashboard(token ?? null);

  if (sharedDashboardQuery.isLoading) {
    return <LoadingState title="Loading shared dashboard" description="Fetching the read-only dashboard payload." />;
  }

  if (sharedDashboardQuery.isError || !sharedDashboardQuery.data) {
    return (
      <ErrorState
        description="Could not load shared dashboard."
        onRetry={() => {
          void sharedDashboardQuery.refetch();
        }}
      />
    );
  }

  const dashboard = sharedDashboardQuery.data;

  return (
    <PageSurface variant="workspace">
      <Stack spacing={3}>
        <PageHeader
          eyebrow="Public dashboard"
          title={dashboard.name}
          description="Shared read-only dashboard. Private actions, editing, and refresh controls are intentionally removed."
          action={<StatusBadge label={formatFreshnessLabel(dashboard.freshness_status)} tone={dashboardFreshnessTone(dashboard.freshness_status)} />}
        />

        <SurfaceCard tone="hero" padding="md">
          <Stack spacing={2.15}>
            <Stack spacing={0.75}>
              <Typography variant="overline" sx={{ color: tokens.color.accent.blue }}>
                Read-only view
              </Typography>
              <Typography variant="h5">
                Shared dashboard
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 780 }}>
                This public surface renders the persisted dashboard state returned by the backend token endpoint, without any authenticated controls.
              </Typography>
            </Stack>

            <MetricStrip accent>
              <MetricStripItem label="Widgets" value={dashboard.widgets.length.toLocaleString()} detail="Visible to viewers" />
              <MetricStripItem label="Last success" value={formatDashboardDateTime(dashboard.last_successful_refresh_at)} detail="Latest successful refresh" />
              <MetricStripItem label="Next refresh" value={formatDashboardDateTime(dashboard.next_refresh_at)} detail="Backend schedule" />
            </MetricStrip>
          </Stack>
        </SurfaceCard>

        <SectionBand
          eyebrow="Narrative"
          title="Current interpretation"
          description="Narrative context remains visible in the shared view, but editing and operational controls stay private."
          density="compact"
          divider="subtle"
        >
          <PublicNarrative
            summary={dashboard.narrative.summary}
            findings={dashboard.narrative.key_findings}
            caveats={dashboard.narrative.risks_or_caveats}
          />
        </SectionBand>

        {dashboard.widgets.length === 0 ? (
          <EmptyState title="No widgets in this shared dashboard" description="The shared link is valid, but the dashboard does not contain persisted widgets yet." />
        ) : (
          <SectionBand
            eyebrow="Canvas"
            title="Shared widgets"
            description="Widgets render in read-only mode and keep the same editorial dashboard composition used in the authenticated app."
            density="compact"
            divider="none"
          >
            <DashboardGrid
              widgets={dashboard.widgets}
              renderWidget={(widget) => <DashboardWidget widget={widget} readOnly onRefresh={() => undefined} />}
            />
          </SectionBand>
        )}
      </Stack>
    </PageSurface>
  );
}
