import type { PropsWithChildren, ReactNode } from "react";
import type { SxProps, Theme } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Box, Stack, Typography } from "@mui/material";

import { tokens } from "@next/theme/tokens";

type SurfaceTone = "panel" | "well" | "quiet" | "hero";
type SurfacePadding = "sm" | "md" | "lg";

export function SurfaceCard({
  title,
  subtitle,
  action,
  tone = "panel",
  padding = "md",
  children,
}: PropsWithChildren<{
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  tone?: SurfaceTone;
  padding?: SurfacePadding;
}>) {
  const paddingMap = {
    sm: { xs: 1.15, md: 1.35 },
    md: { xs: 1.45, md: 1.75 },
    lg: { xs: 1.8, md: 2.05 },
  } as const;

  const toneStyles = {
    panel: {
      backgroundColor: tokens.color.bg.surface,
      border: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
      borderTop: `2px solid ${alpha(tokens.color.accent.deepGreen, 0.42)}`,
      borderRadius: tokens.radius.md,
    },
    well: {
      backgroundColor: alpha(tokens.color.bg.surfaceMuted, 0.7),
      border: `1px solid ${alpha(tokens.color.border.subtle, 0.92)}`,
      borderRadius: tokens.radius.sm,
    },
    quiet: {
      backgroundColor: "transparent",
      border: "none",
      borderRadius: 0,
    },
    hero: {
      backgroundColor: alpha(tokens.color.bg.surface, 0.82),
      borderTop: `1px solid ${tokens.color.border.subtle}`,
      borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
      borderLeft: "none",
      borderRight: "none",
      borderRadius: 0,
    },
  } as const;

  return (
    <Box sx={{ ...toneStyles[tone] }}>
      <Stack spacing={tokens.spacing.blockGap / 8} sx={{ p: paddingMap[padding] }}>
        {title || subtitle || action ? (
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={1.15}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", md: "flex-end" }}
          >
            <Stack spacing={0.65}>
              {typeof title === "string" ? <Typography variant="h5">{title}</Typography> : title}
              {typeof subtitle === "string" ? (
                <Typography variant="body2" color="text.secondary">
                  {subtitle}
                </Typography>
              ) : (
                subtitle
              )}
            </Stack>
            {action}
          </Stack>
        ) : null}
        <Stack spacing={tokens.spacing.elementGap / 8}>{children}</Stack>
      </Stack>
    </Box>
  );
}

export function InverseHeroCard({ children }: PropsWithChildren) {
  return (
    <Box
      sx={{
        borderTop: `1px solid ${tokens.color.border.subtle}`,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.32)}`,
        backgroundColor: alpha(tokens.color.bg.inverse, 0.02),
      }}
    >
      <Box sx={{ py: { xs: 2.05, md: 2.35 } }}>{children}</Box>
    </Box>
  );
}

export function OpenSection({
  children,
  divider = "top",
  spacing = 2,
  sx,
}: PropsWithChildren<{ divider?: "none" | "top" | "bottom" | "both"; spacing?: number; sx?: SxProps<Theme> }>) {
  const topBorder = divider === "top" || divider === "both";
  const bottomBorder = divider === "bottom" || divider === "both";

  return (
    <Stack
      spacing={spacing}
      sx={{
        py: 1.5,
        borderTop: topBorder ? `1px solid ${alpha(tokens.color.border.strong, 0.26)}` : "none",
        borderBottom: bottomBorder ? `1px solid ${alpha(tokens.color.border.strong, 0.26)}` : "none",
        ...sx,
      }}
    >
      {children}
    </Stack>
  );
}

export function SectionBlock({
  title,
  eyebrow,
  description,
  action,
  children,
  divider = "top",
}: PropsWithChildren<{
  title?: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  divider?: "none" | "top" | "bottom" | "both";
}>) {
  return (
    <OpenSection divider={divider} spacing={1.5}>
      {eyebrow || title || description || action ? (
        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={1.25}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", lg: "flex-start" }}
        >
          <Stack spacing={0.6} sx={{ maxWidth: 920 }}>
            {typeof eyebrow === "string" ? (
              <Typography variant="overline" color="text.secondary">
                {eyebrow}
              </Typography>
            ) : (
              eyebrow
            )}
            {typeof title === "string" ? <Typography variant="h6">{title}</Typography> : title}
            {typeof description === "string" ? (
              <Typography variant="body2" color="text.secondary">
                {description}
              </Typography>
            ) : (
              description
            )}
          </Stack>
          {action}
        </Stack>
      ) : null}
      {children}
    </OpenSection>
  );
}

export function SectionBand({
  title,
  eyebrow,
  description,
  action,
  children,
  density = "comfortable",
  divider = "subtle",
}: PropsWithChildren<{
  title?: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  density?: "compact" | "comfortable" | "roomy";
  divider?: "none" | "subtle" | "strong";
}>) {
  const densityMap = {
    compact: { xs: 1.85, md: 2.15, content: 1.75 },
    comfortable: { xs: 2.35, md: 2.75, content: 2.15 },
    roomy: { xs: 2.85, md: 3.2, content: 2.65 },
  } as const;

  const borderColor =
    divider === "none"
      ? "transparent"
      : divider === "strong"
        ? alpha(tokens.color.border.strong, 0.42)
        : alpha(tokens.color.border.strong, 0.24);

  return (
    <Stack
      spacing={densityMap[density].content}
      sx={{
        py: { xs: densityMap[density].xs, md: densityMap[density].md },
        borderBottom: divider === "none" ? "none" : `1px solid ${borderColor}`,
      }}
    >
      {eyebrow || title || description || action ? (
        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={1.85}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", lg: "flex-end" }}
        >
          <Stack spacing={0.75} sx={{ maxWidth: 960 }}>
            {typeof eyebrow === "string" ? (
              <Typography variant="overline" color="text.secondary">
                {eyebrow}
              </Typography>
            ) : (
              eyebrow
            )}
            {typeof title === "string" ? <Typography variant="h4">{title}</Typography> : title}
            {typeof description === "string" ? (
              <Typography color="text.secondary" sx={{ maxWidth: 820 }}>
                {description}
              </Typography>
            ) : (
              description
            )}
          </Stack>
          {action}
        </Stack>
      ) : null}
      {children}
    </Stack>
  );
}

export function InlineStatRow({
  children,
  columns = 3,
  divider = "both",
}: PropsWithChildren<{ columns?: 2 | 3 | 4; divider?: "none" | "top" | "bottom" | "both" }>) {
  const topBorder = divider === "top" || divider === "both";
  const bottomBorder = divider === "bottom" || divider === "both";

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          sm: columns === 2 ? "repeat(2, minmax(0, 1fr))" : "repeat(2, minmax(0, 1fr))",
          lg: `repeat(${columns}, minmax(0, 1fr))`,
        },
        gap: "1px",
        borderTop: topBorder ? `1px solid ${alpha(tokens.color.border.strong, 0.22)}` : "none",
        borderBottom: bottomBorder ? `1px solid ${alpha(tokens.color.border.strong, 0.22)}` : "none",
        backgroundColor: alpha(tokens.color.border.strong, 0.2),
        "& > :nth-of-type(3):last-child": {
          gridColumn: { sm: "1 / -1", lg: "auto" },
        },
      }}
    >
      {children}
    </Box>
  );
}

export function InlineStatItem({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <Stack
      spacing={0.45}
      sx={{
        py: { xs: 1.15, md: 1.35 },
        px: { xs: 1.15, sm: 1.2, lg: 1.45 },
        minWidth: 0,
        backgroundColor: tokens.color.bg.surface,
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ letterSpacing: "0.06em", textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Typography variant="subtitle1" sx={{ lineHeight: 1.3 }}>
        {value}
      </Typography>
      {typeof detail === "string" ? (
        <Typography variant="body2" color="text.secondary">
          {detail}
        </Typography>
      ) : (
        detail
      )}
    </Stack>
  );
}

export function MetricStrip({
  children,
  desktopColumns = 3,
}: PropsWithChildren<{ desktopColumns?: 3 | 4 }>) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          sm: "repeat(2, minmax(0, 1fr))",
          lg: `repeat(${desktopColumns}, minmax(220px, 1fr))`,
        },
        alignItems: "stretch",
        gap: "1px",
        backgroundColor: alpha(tokens.color.border.strong, 0.18),
        borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.2)}`,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.2)}`,
        "& > :nth-of-type(3):last-child": {
          gridColumn: { sm: "1 / -1", lg: "auto" },
        },
      }}
    >
      {children}
    </Box>
  );
}

export function MetricStripItem({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <Stack
      spacing={0.55}
      sx={{
        py: { xs: 1.25, md: 1.45 },
        px: { xs: 1.15, sm: 1.15, lg: 1.45 },
        minWidth: 0,
        backgroundColor: tokens.color.bg.surface,
        justifyContent: "center",
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ letterSpacing: "0.06em", textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Typography variant="h6" sx={{ lineHeight: 1.24, overflowWrap: "normal", wordBreak: "normal", hyphens: "none" }}>
        {value}
      </Typography>
      {typeof detail === "string" ? (
        <Typography variant="body2" color="text.secondary" title={detail}>
          {detail}
        </Typography>
      ) : (
        detail
      )}
    </Stack>
  );
}
