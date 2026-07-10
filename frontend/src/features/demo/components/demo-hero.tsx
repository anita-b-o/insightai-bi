import type { ReactNode } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";

import { GeoPattern } from "@next/components/brand/geo-pattern";
import { InsightBrand } from "@next/components/brand/insight-brand";
import { InlineStatItem, InlineStatRow, InverseHeroCard } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import type { DemoExperience } from "../types";

export function DemoHero({ demo }: { demo: DemoExperience }) {
  return (
    <Box sx={{ position: "relative", overflow: "hidden", borderRadius: tokens.radius.lg, backgroundColor: tokens.color.bg.surface }}>
      <GeoPattern density="quiet" sx={{ left: "auto", width: { xs: 180, sm: 260, md: 380 }, opacity: { xs: 0.1, sm: 0.16, md: 0.2 } }} />
      <InverseHeroCard>
      <Stack spacing={2.15} sx={{ position: "relative", zIndex: 1 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "flex-end" }}>
          <Stack spacing={1.25} sx={{ maxWidth: 840 }}>
            <InsightBrand />
            <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
              Public BI walkthrough
            </Typography>
            <Typography variant="h4">
              InsightAI BI Demo
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
              Turn questions into clear decisions with dataset profiling, Ask AI, ranked insights, and persistent dashboards in one read-only walkthrough.
            </Typography>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
            <Button variant="contained" component={RouterLink} to="/register">
              Create account
            </Button>
            <Button variant="outlined" component={RouterLink} to="/login">
              Sign in
            </Button>
          </Stack>
        </Stack>

        <InlineStatRow columns={3}>
          <InlineStatItem label="Dataset" value={demo.dataset.name} detail="Analysis sample" />
          <InlineStatItem label="Coverage" value={`${demo.dataset.rowCount} rows · ${demo.dataset.columnCount} columns`} detail="Compact BI walkthrough" />
          <InlineStatItem
            label="Flow"
            value={
              <Stack direction="row" spacing={0.8} flexWrap="wrap" useFlexGap>
                <Chip label="Ask AI" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.signal, 0.16), color: tokens.color.fg.primary }} />
                <Chip label="Insights" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.orange, 0.12), color: tokens.color.fg.primary }} />
                <Chip label="Dashboard" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.deepGreen, 0.1), color: tokens.color.fg.primary }} />
              </Stack>
            }
            detail="Same product flow"
          />
        </InlineStatRow>
      </Stack>
      </InverseHeroCard>
    </Box>
  );
}
