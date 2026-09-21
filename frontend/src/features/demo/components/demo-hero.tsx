import type { ReactNode } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";

import { InsightBrand } from "@next/components/brand/insight-brand";
import { InlineStatItem, InlineStatRow } from "@next/components/ui/surface-card";
import foxImage from "@next/assets/brand/fox.png";
import { tokens } from "@next/theme/tokens";

import type { DemoExperience } from "../types";

export function DemoHero({ demo }: { demo: DemoExperience }) {
  return (
    <Box
      data-testid="demo-hero"
      sx={{
        width: "100%",
        position: "relative",
        overflow: "hidden",
        borderBottom: `1px solid ${tokens.color.border.strong}`,
        backgroundColor: tokens.color.bg.surface,
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1.1fr) minmax(320px, 0.9fr)" },
      }}
    >
      <Box
        sx={{
          width: "100%",
          px: { xs: 2, md: 5, xl: 7 },
          py: { xs: 3, md: 6 },
        }}
      >
        <Stack data-testid="demo-hero-content" spacing={2.15} sx={{ position: "relative", zIndex: 1 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between" alignItems={{ xs: "flex-start", md: "flex-end" }}>
            <Stack spacing={1.25} sx={{ maxWidth: 840 }}>
              <InsightBrand />
              <Typography variant="overline" sx={{ color: tokens.color.accent.blue, letterSpacing: "0.12em" }}>
                Public BI walkthrough
              </Typography>
              <Typography variant="h4">InsightAI BI Demo</Typography>
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
        </Stack>
        <Box sx={{ position: "relative", zIndex: 1, pt: 3 }}>
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
        </Box>
      </Box>
      <Box sx={{ display: { xs: "none", md: "block" }, position: "relative", overflow: "hidden", backgroundColor: "#000", borderLeft: `1px solid ${tokens.color.border.strong}`, minHeight: 460 }}>
        <Box component="img" src={foxImage} alt="" aria-hidden sx={{ position: "absolute", width: "118%", maxWidth: "none", right: "-17%", top: "50%", transform: "translateY(-50%)", objectFit: "contain" }} />
      </Box>
    </Box>
  );
}
