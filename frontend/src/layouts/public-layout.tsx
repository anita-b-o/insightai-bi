import type { PropsWithChildren } from "react";
import { Box } from "@mui/material";

import { AppFooter } from "@next/components/ui/app-footer";
import { PageSurface } from "@next/components/ui/page-surface";

import { NextThemeBoundary } from "./theme-boundary";

export function NextPublicLayout({ children, framed = true }: PropsWithChildren<{ framed?: boolean }>) {
  return (
    <NextThemeBoundary>
      <Box sx={{ minHeight: "100dvh", display: "flex", flexDirection: "column" }}>
        <Box sx={{ flex: 1 }}>{framed ? <PageSurface>{children}</PageSurface> : children}</Box>
        <AppFooter />
      </Box>
    </NextThemeBoundary>
  );
}
