import type { ReactNode } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";

import { InverseHeroCard } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import type { DemoExperience } from "../types";

export function DemoHero({ demo }: { demo: DemoExperience }) {
  return (
    <InverseHeroCard>
      <Stack spacing={2.15}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "flex-end" }}>
          <Stack spacing={1.25} sx={{ maxWidth: 840 }}>
            <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
              Editorial BI walkthrough
            </Typography>
            <Typography variant="h4">
              InsightAI BI Demo
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
              A curated product walkthrough showing how dataset profiling, Ask AI, ranked insights, and persistent dashboards connect into one BI workflow without requiring authentication.
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

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
            gap: 1.05,
          }}
        >
          <MiniStat label="Dataset" value={demo.dataset.name} detail="Analysis sample" />
          <MiniStat label="Coverage" value={`${demo.dataset.rowCount} rows · ${demo.dataset.columnCount} columns`} detail="Compact BI walkthrough" />
          <MiniStat
            label="Flow"
            value={
              <Stack direction="row" spacing={0.8} flexWrap="wrap" useFlexGap>
                <Chip label="Ask AI" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.blue, 0.08), color: tokens.color.fg.primary }} />
                <Chip label="Insights" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.blue, 0.08), color: tokens.color.fg.primary }} />
                <Chip label="Dashboard" size="small" sx={{ backgroundColor: alpha(tokens.color.accent.blue, 0.08), color: tokens.color.fg.primary }} />
              </Stack>
            }
            detail="Same product flow"
          />
        </Box>
      </Stack>
    </InverseHeroCard>
  );
}

function MiniStat({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail: string;
}) {
  return (
    <Stack
      spacing={0.75}
      sx={{
        p: { xs: 1.35, md: 1.45 },
        borderRadius: tokens.radius.xs,
        border: `1px solid ${alpha(tokens.color.border.subtle, 0.8)}`,
        backgroundColor: tokens.color.bg.surface,
        minWidth: 0,
        minHeight: 116,
        justifyContent: "space-between",
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {label}
      </Typography>
      {typeof value === "string" ? (
        <Typography variant="subtitle1" sx={{ lineHeight: 1.28 }}>
          {value}
        </Typography>
      ) : (
        value
      )}
      <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "normal" }}>
        {detail}
      </Typography>
    </Stack>
  );
}
