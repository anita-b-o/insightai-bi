import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

import { GeoPattern } from "@next/components/brand/geo-pattern";
import { InsightBrand } from "@next/components/brand/insight-brand";
import { NextThemeBoundary } from "./theme-boundary";
import { tokens } from "@next/theme/tokens";

export function NextAuthLayout({ children }: { children: ReactNode }) {
  return (
    <NextThemeBoundary>
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(420px, 0.95fr) minmax(460px, 1.05fr)" },
          px: { xs: 2, md: 3 },
          py: { xs: 3, md: 4 },
          gap: { xs: 3, lg: 4 },
          background: tokens.color.bg.canvas,
        }}
      >
        <Box
          sx={{
            position: "relative",
            minHeight: { xs: 260, lg: "calc(100vh - 64px)" },
            borderRadius: tokens.radius.lg,
            overflow: "hidden",
            backgroundColor: tokens.color.bg.inverse,
            color: tokens.color.fg.inverse,
            p: { xs: 2.2, md: 3 },
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <GeoPattern inverted density="bold" sx={{ opacity: 0.34 }} />
          <Stack spacing={2.2} sx={{ position: "relative", zIndex: 1, maxWidth: 540 }}>
            <InsightBrand tone="inverse" />
            <Typography variant="h2" sx={{ color: tokens.color.fg.inverse, maxWidth: 520 }}>
              Find the signal. Build the story.
            </Typography>
            <Typography sx={{ color: "rgba(255, 253, 247, 0.78)", maxWidth: 500 }}>
              SQL-backed exploration, persistent dashboards, and BI workflows shaped for clear decisions.
            </Typography>
          </Stack>
          <Typography variant="overline" sx={{ position: "relative", zIndex: 1, color: "rgba(255, 253, 247, 0.72)" }}>
            Data, interpreted.
          </Typography>
        </Box>

        <Stack spacing={2.35} sx={{ width: "100%", maxWidth: 520, alignSelf: "center", justifySelf: "center" }}>
          <Box sx={{ maxWidth: 460, width: "100%" }}>{children}</Box>
        </Stack>
      </Box>
    </NextThemeBoundary>
  );
}
