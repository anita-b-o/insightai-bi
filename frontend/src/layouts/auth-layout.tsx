import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

import { NextThemeBoundary } from "./theme-boundary";
import { tokens } from "@next/theme/tokens";

export function NextAuthLayout({ children }: { children: ReactNode }) {
  return (
    <NextThemeBoundary>
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          px: 2,
          background: tokens.color.bg.canvas,
        }}
      >
        <Stack spacing={2.35} sx={{ width: "100%", maxWidth: 520 }}>
          <Stack spacing={0.9}>
            <Typography variant="overline" color="text.secondary">
              InsightAI BI
            </Typography>
            <Typography variant="h2" sx={{ maxWidth: 520 }}>
              Modern analytics for AI-native teams.
            </Typography>
            <Typography color="text.secondary">
              SQL-backed exploration, persistent dashboards, and premium BI workflows without changing your backend.
            </Typography>
          </Stack>
          <Box sx={{ maxWidth: 460 }}>{children}</Box>
        </Stack>
      </Box>
    </NextThemeBoundary>
  );
}
