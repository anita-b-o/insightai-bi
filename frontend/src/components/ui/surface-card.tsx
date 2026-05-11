import type { PropsWithChildren, ReactNode } from "react";
import { alpha } from "@mui/material/styles";
import { Box, Card, CardContent, Stack, Typography } from "@mui/material";

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
    sm: { xs: 1.35, md: 1.65 },
    md: { xs: 1.7, md: 2 },
    lg: { xs: 2.05, md: 2.35 },
  } as const;

  const toneStyles = {
    panel: {
      backgroundColor: tokens.color.bg.surface,
      border: `1px solid ${alpha(tokens.color.border.subtle, 0.74)}`,
      boxShadow: "none",
    },
    well: {
      backgroundColor: alpha(tokens.color.bg.surface, 0.98),
      border: `1px solid ${alpha(tokens.color.border.strong, 0.42)}`,
      boxShadow: "none",
    },
    quiet: {
      backgroundColor: "transparent",
      border: "none",
      boxShadow: "none",
    },
    hero: {
      backgroundColor: tokens.color.bg.surface,
      border: `1px solid ${alpha(tokens.color.border.strong, 0.56)}`,
      boxShadow: "none",
    },
  } as const;

  return (
    <Card
      sx={{
        ...toneStyles[tone],
        borderRadius: tone === "hero" ? tokens.radius.lg : tone === "well" ? tokens.radius.sm : tokens.radius.md,
      }}
    >
      <CardContent sx={{ p: paddingMap[padding] }}>
        <Stack spacing={tokens.spacing.blockGap / 8}>
          {title || subtitle || action ? (
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.5}
              justifyContent="space-between"
              alignItems={{ xs: "flex-start", md: "center" }}
            >
              <Stack spacing={0.95}>
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
      </CardContent>
    </Card>
  );
}

export function InverseHeroCard({ children }: PropsWithChildren) {
  return (
    <Card
      sx={{
        background: tokens.color.bg.surface,
        color: tokens.color.fg.primary,
        border: `1px solid ${alpha(tokens.color.border.strong, 0.56)}`,
        boxShadow: "none",
        position: "relative",
        overflow: "hidden",
        borderRadius: tokens.radius.md,
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          background: "none",
          pointerEvents: "none",
        }}
      />
      <CardContent sx={{ p: { xs: 1.8, md: 2.1 }, position: "relative" }}>{children}</CardContent>
    </Card>
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
    compact: { xs: 2, md: 2.3, content: 2.05 },
    comfortable: { xs: 2.5, md: 3, content: tokens.spacing.blockGap / 8 },
    roomy: { xs: 3, md: 3.5, content: 3 },
  } as const;

  const borderColor =
    divider === "none"
      ? "transparent"
      : divider === "strong"
        ? alpha(tokens.color.border.strong, 0.52)
        : alpha(tokens.color.border.strong, 0.32);

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
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", lg: "flex-end" }}
        >
          <Stack spacing={1} sx={{ maxWidth: 960 }}>
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

export function MetricStrip({
  children,
  desktopColumns = 3,
  accent = false,
}: PropsWithChildren<{ desktopColumns?: 3 | 4; accent?: boolean }>) {
  return (
    <Box
      sx={{
        position: "relative",
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          sm: "repeat(2, minmax(0, 1fr))",
          lg: `repeat(${desktopColumns}, minmax(220px, 1fr))`,
        },
        alignItems: "stretch",
        gap: "1px",
        backgroundColor: alpha(tokens.color.border.strong, 0.2),
        borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.2)}`,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.2)}`,
        overflow: "hidden",
        "&::before": accent
          ? {
              content: '""',
              position: "absolute",
              insetInline: 0,
              top: 0,
              height: 2,
              backgroundColor: alpha(tokens.color.accent.blue, 0.85),
            }
          : undefined,
      }}
    >
      {children}
    </Box>
  );
}

export function MetricStripItem({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <Stack
      spacing={0.75}
      sx={{
        py: { xs: 1.6, md: 1.8 },
        px: { xs: 0.35, sm: 1.35, lg: 1.7 },
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
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            lineHeight: 1.5,
            whiteSpace: { xs: "normal", lg: "nowrap" },
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={detail}
        >
          {detail}
        </Typography>
      ) : (
        detail
      )}
    </Stack>
  );
}
