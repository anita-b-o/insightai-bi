import type { ReactNode } from "react";
import { alpha } from "@mui/material/styles";
import { Box, Stack, Typography } from "@mui/material";

import { GeoPattern } from "@next/components/brand/geo-pattern";
import { tokens } from "@next/theme/tokens";

export function PageHeader({
  title,
  description,
  action,
  eyebrow,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <Stack
      direction={{ xs: "column", lg: "row" }}
      spacing={2.5}
      justifyContent="space-between"
      alignItems={{ xs: "flex-start", lg: "flex-end" }}
      sx={{
        position: "relative",
        overflow: "hidden",
        px: { xs: 1.4, md: 1.8 },
        py: { xs: 1.45, md: 1.75 },
        borderRadius: tokens.radius.lg,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.28)}`,
        background: `linear-gradient(135deg, ${alpha(tokens.color.bg.surface, 0.92)} 0%, ${alpha(tokens.color.bg.elevated, 0.8)} 100%)`,
      }}
    >
      <GeoPattern density="quiet" sx={{ display: { xs: "none", sm: "block" }, left: "auto", width: { sm: 220, md: 320 }, opacity: 0.18 }} />
      <Stack spacing={1} sx={{ position: "relative", zIndex: 1 }}>
        {typeof eyebrow === "string" ? (
          <Typography variant="overline" color="text.secondary">
            {eyebrow}
          </Typography>
        ) : (
          eyebrow
        )}
        {typeof title === "string" ? (
          <Typography variant="h3" sx={{ maxWidth: 920 }}>
            {title}
          </Typography>
        ) : (
          title
        )}
        {typeof description === "string" ? (
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 880 }}>
            {description}
          </Typography>
        ) : (
          description
        )}
      </Stack>
      {action ? <Box sx={{ position: "relative", zIndex: 1 }}>{action}</Box> : null}
    </Stack>
  );
}
