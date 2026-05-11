import { Stack, Typography } from "@mui/material";

import { SectionBand } from "@next/components/ui/surface-card";
import { alpha } from "@mui/material/styles";
import { tokens } from "@next/theme/tokens";
import { DashboardGrid } from "@next/features/dashboards/components/dashboard-grid";
import { DashboardWidget } from "@next/features/dashboards/components/dashboard-widget";

import type { DemoExperience } from "../types";

export function DemoDashboardPreview({ demo }: { demo: DemoExperience }) {
  return (
    <SectionBand
      eyebrow="Saved workspace"
      title="Demo dashboard"
      description="Persistent widgets, saved layout, and a narrative already prepared for walkthroughs and stakeholder review."
    >
      <Stack spacing={3}>
        <Stack
          spacing={1.2}
          sx={{
            p: { xs: 2, md: 2.25 },
            backgroundColor: alpha(tokens.color.bg.rail, 0.9),
            borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
            borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
          }}
        >
          <Typography variant="overline" color="text.secondary">
            Dashboard narrative
          </Typography>
          <Typography variant="h4">Saved workspace summary</Typography>
          <Typography color="text.secondary">{demo.dashboardNarrative.summary}</Typography>
          <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2.2 }}>
            {demo.dashboardNarrative.key_findings.map((item) => (
              <Typography key={item} component="li" variant="body2" color="text.secondary">
                {item}
              </Typography>
            ))}
          </Stack>
        </Stack>

        <DashboardGrid
          widgets={demo.dashboard.widgets}
          renderWidget={(widget) => <DashboardWidget widget={widget} readOnly onRefresh={() => undefined} />}
        />
      </Stack>
    </SectionBand>
  );
}
