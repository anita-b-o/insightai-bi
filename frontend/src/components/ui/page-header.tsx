import type { ReactNode } from "react";
import { alpha } from "@mui/material/styles";
import { Stack, Typography } from "@mui/material";

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
        pb: 2,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.46)}`,
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          left: 0,
          bottom: -1,
          width: { xs: 52, md: 84 },
          height: 2,
          background: `linear-gradient(90deg, ${tokens.color.accent.blue} 0%, ${tokens.color.accent.cyan} 100%)`,
        },
      }}
    >
      <Stack spacing={1}>
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
      {action}
    </Stack>
  );
}
