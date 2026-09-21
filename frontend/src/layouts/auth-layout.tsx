import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

import { InsightBrand } from "@next/components/brand/insight-brand";
import foxImage from "@next/assets/brand/fox.png";
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
          p: { xs: 0, md: 2 },
          gap: 0,
          background: tokens.color.bg.canvas,
        }}
      >
        <Box
          sx={{
            position: "relative",
            display: { xs: "none", md: "flex" },
            minHeight: "calc(100vh - 32px)",
            borderRadius: tokens.radius.md,
            overflow: "hidden",
            backgroundColor: "#000",
            color: tokens.color.fg.inverse,
            flexDirection: "column",
            justifyContent: "space-between",
            p: { md: 3, xl: 4 },
            border: `1px solid ${tokens.color.border.strong}`,
          }}
        >
          <Box component="img" src={foxImage} alt="" aria-hidden sx={{ position: "absolute", width: { md: "88%", xl: "76%" }, right: { md: "-14%", xl: "-7%" }, top: "8%", objectFit: "contain" }} />
          <Stack spacing={2.2} sx={{ position: "relative", zIndex: 1, maxWidth: 500, mt: "auto" }}>
            <InsightBrand tone="inverse" />
            <Typography variant="h2" sx={{ color: tokens.color.fg.inverse, maxWidth: 520 }}>
              Find the signal. Build the story.
            </Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.76)", maxWidth: 500 }}>
              SQL-backed exploration, persistent dashboards, and BI workflows shaped for clear decisions.
            </Typography>
          </Stack>
        </Box>

        <Stack spacing={2.35} sx={{ width: "100%", maxWidth: 520, alignSelf: "center", justifySelf: "center", px: { xs: 2, sm: 4 }, py: { xs: 4, md: 2 } }}>
          <Box sx={{ maxWidth: 460, width: "100%" }}>{children}</Box>
        </Stack>
      </Box>
    </NextThemeBoundary>
  );
}
