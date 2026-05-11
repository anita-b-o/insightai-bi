import type { PropsWithChildren } from "react";
import { Box } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { tokens } from "@next/theme/tokens";

export function PageSurface({
  children,
  tone = "default",
  variant = "default",
}: PropsWithChildren<{ tone?: "default" | "muted"; variant?: "default" | "workspace" }>) {
  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: tokens.layout.appMaxWidth,
        mx: "auto",
        px: variant === "workspace" ? { xs: 2, md: 3.25, xl: 4 } : { xs: 2, md: 3, xl: 3.5 },
        py: variant === "workspace" ? { xs: 3, md: 4.5 } : { xs: 3, md: 4.5 },
        backgroundColor: tone === "muted" ? alpha(tokens.color.bg.surface, 0.92) : "transparent",
      }}
    >
      {children}
    </Box>
  );
}
