import { alpha } from "@mui/material/styles";
import { Button, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { StatusBadge } from "@next/components/ui/status-badge";
import { OpenSection } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import { dashboardFreshnessTone, formatDashboardDateTime, formatFreshnessLabel, type DashboardSummary } from "../types";

export function DashboardCard({ dashboard }: { dashboard: DashboardSummary }) {
  return (
    <OpenSection divider="top" spacing={1}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", md: "center" }}
        sx={{
          py: 0.75,
          position: "relative",
          "&::before": {
            content: '""',
            position: "absolute",
            left: 0,
            top: 0,
            width: 28,
            height: 1,
            bgcolor: tokens.color.accent.blue,
            opacity: 0.7,
          },
        }}
      >
        <Stack spacing={0.75} sx={{ minWidth: 0 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ xs: "flex-start", sm: "center" }} useFlexGap flexWrap="wrap">
            <Typography variant="h6" sx={{ minWidth: 0 }}>
              {dashboard.name}
            </Typography>
            <StatusBadge label={formatFreshnessLabel(dashboard.freshness_status)} tone={dashboardFreshnessTone(dashboard.freshness_status)} />
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {dashboard.widget_count} widgets • Updated {formatDashboardDateTime(dashboard.updated_at)}
          </Typography>
        </Stack>

        <Button component={RouterLink} to={`/dashboards/${dashboard.id}`} variant="outlined">
          Open dashboard
        </Button>
      </Stack>
    </OpenSection>
  );
}
