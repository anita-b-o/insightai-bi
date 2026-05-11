import { Stack } from "@mui/material";

import { DashboardCard } from "./dashboard-card";
import type { DashboardSummary } from "../types";

export function DashboardList({ dashboards }: { dashboards: DashboardSummary[] }) {
  return (
    <Stack spacing={0}>
      {dashboards.map((dashboard) => (
        <DashboardCard key={dashboard.id} dashboard={dashboard} />
      ))}
    </Stack>
  );
}
