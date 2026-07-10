import type { SxProps, Theme } from "@mui/material";
import { Box, Stack, Typography } from "@mui/material";

import { tokens } from "@next/theme/tokens";

type BrandTone = "light" | "dark" | "inverse";
type BrandVariant = "mark" | "lockup";

function resolveColors(tone: BrandTone) {
  if (tone === "inverse") {
    return {
      field: tokens.color.bg.surface,
      fieldStroke: tokens.color.bg.surface,
      circle: tokens.color.accent.signal,
      wedge: tokens.color.accent.orange,
      slash: tokens.color.accent.deepGreen,
      node: tokens.color.accent.deepGreen,
      text: tokens.color.fg.inverse,
      subtext: "rgba(255, 253, 247, 0.72)",
    };
  }

  if (tone === "dark") {
    return {
      field: tokens.color.accent.deepGreen,
      fieldStroke: tokens.color.accent.deepGreen,
      circle: tokens.color.accent.signal,
      wedge: tokens.color.accent.orange,
      slash: tokens.color.bg.surface,
      node: tokens.color.bg.surface,
      text: tokens.color.fg.primary,
      subtext: tokens.color.fg.secondary,
    };
  }

  return {
    field: tokens.color.bg.surface,
    fieldStroke: tokens.color.border.strong,
    circle: tokens.color.accent.signal,
    wedge: tokens.color.accent.orange,
    slash: tokens.color.accent.deepGreen,
    node: tokens.color.accent.deepGreen,
    text: tokens.color.fg.primary,
    subtext: tokens.color.fg.secondary,
  };
}

export function InsightMark({
  size = 42,
  tone = "light",
  sx,
  title,
}: {
  size?: number;
  tone?: BrandTone;
  sx?: SxProps<Theme>;
  title?: string;
}) {
  const colors = resolveColors(tone);
  const ariaProps = title ? { role: "img", "aria-label": title } : { "aria-hidden": true };

  return (
    <Box
      component="svg"
      viewBox="0 0 64 64"
      {...ariaProps}
      sx={{
        width: size,
        height: size,
        display: "block",
        flexShrink: 0,
        overflow: "visible",
        ...sx,
      }}
    >
      {title ? <title>{title}</title> : null}
      <rect x="2" y="2" width="60" height="60" rx="9" fill={colors.field} stroke={colors.fieldStroke} strokeWidth="2" />
      <path d="M10 12H54V28H10z" fill={colors.circle} />
      <path d="M10 28H26V54H10z" fill={tokens.color.bg.tint} opacity="0.95" />
      <circle cx="38" cy="39" r="15" fill={colors.circle} />
      <path d="M23 16A22 22 0 0 1 45 38H23z" fill={colors.wedge} />
      <path d="M19 35L48 25L55 39L26 49z" fill={colors.slash} />
      <circle cx="18" cy="18" r="4.4" fill={colors.node} />
      <circle cx="48" cy="48" r="4.4" fill={colors.node} />
      <path d="M18 18L36 35L48 48" fill="none" stroke={colors.node} strokeWidth="3" strokeLinecap="round" opacity="0.9" />
    </Box>
  );
}

export function InsightBrand({
  variant = "lockup",
  tone = "light",
  compact = false,
  sx,
}: {
  variant?: BrandVariant;
  tone?: BrandTone;
  compact?: boolean;
  sx?: SxProps<Theme>;
}) {
  const colors = resolveColors(tone);

  if (variant === "mark") {
    return <InsightMark tone={tone} size={compact ? 34 : 42} title="InsightAI BI" sx={sx} />;
  }

  return (
    <Stack direction="row" spacing={1.15} alignItems="center" sx={{ minWidth: 0, ...sx }}>
      <InsightMark tone={tone} size={compact ? 36 : 44} title="InsightAI BI" />
      <Box sx={{ minWidth: 0 }}>
        <Typography variant={compact ? "subtitle2" : "subtitle1"} sx={{ color: colors.text, fontWeight: 800, lineHeight: 1.1 }} noWrap>
          InsightAI BI
        </Typography>
        {!compact ? (
          <Typography variant="caption" sx={{ color: colors.subtext, fontWeight: 700 }} noWrap>
            Data, interpreted.
          </Typography>
        ) : null}
      </Box>
    </Stack>
  );
}
