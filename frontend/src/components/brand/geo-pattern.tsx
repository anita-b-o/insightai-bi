import type { SxProps, Theme } from "@mui/material";
import { Box } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { tokens } from "@next/theme/tokens";

type PatternDensity = "quiet" | "standard" | "bold";

export function GeoPattern({
  density = "standard",
  inverted = false,
  sx,
}: {
  density?: PatternDensity;
  inverted?: boolean;
  sx?: SxProps<Theme>;
}) {
  const opacity = density === "bold" ? 0.98 : density === "standard" ? 0.72 : 0.42;
  const green = inverted ? tokens.color.bg.surface : tokens.color.accent.deepGreen;
  const cream = inverted ? alpha(tokens.color.bg.surface, 0.78) : tokens.color.bg.surface;
  const orange = tokens.color.accent.orange;
  const yellow = tokens.color.accent.signal;
  const beige = tokens.color.bg.tint;

  return (
    <Box
      aria-hidden
      sx={{
        pointerEvents: "none",
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        opacity,
        ...sx,
      }}
    >
      <Box
        component="svg"
        viewBox="0 0 720 420"
        preserveAspectRatio="none"
        sx={{ width: "100%", height: "100%", display: "block" }}
      >
        <defs>
          <pattern id="paper-grain" width="32" height="32" patternUnits="userSpaceOnUse">
            <circle cx="4" cy="7" r="0.7" fill={alpha(tokens.color.fg.primary, inverted ? 0.1 : 0.08)} />
            <circle cx="18" cy="17" r="0.55" fill={alpha(tokens.color.fg.primary, inverted ? 0.12 : 0.08)} />
            <circle cx="29" cy="4" r="0.5" fill={alpha(tokens.color.fg.primary, inverted ? 0.1 : 0.07)} />
          </pattern>
        </defs>
        <rect width="720" height="420" fill="url(#paper-grain)" opacity="0.45" />
        <rect x="0" y="0" width="150" height="120" fill={cream} />
        <rect x="150" y="0" width="390" height="92" fill={orange} />
        <rect x="540" y="0" width="180" height="92" fill={green} />
        <rect x="0" y="92" width="180" height="230" fill={yellow} />
        <rect x="180" y="92" width="390" height="230" fill={green} />
        <rect x="570" y="92" width="150" height="230" fill={beige} />
        <rect x="0" y="322" width="330" height="98" fill={green} />
        <rect x="330" y="322" width="390" height="98" fill={orange} />
        <circle cx="88" cy="48" r="27" fill={green} />
        <circle cx="226" cy="47" r="27" fill={beige} />
        <circle cx="632" cy="48" r="27" fill={cream} />
        <path d="M226 116A116 116 0 0 1 342 232H226z" fill={cream} />
        <circle cx="385" cy="248" r="72" fill={yellow} />
        <path d="M300 190L490 145L545 235L350 275z" fill={green} />
        <path d="M180 92C230 130 230 175 180 212z" fill={cream} />
        <path d="M0 102C52 118 62 154 0 184z" fill={green} />
        <path d="M0 217C64 228 66 272 0 304z" fill={green} />
        <circle cx="642" cy="366" r="50" fill={green} />
        <rect x="640" y="316" width="80" height="100" fill={cream} opacity="0.9" />
        <path d="M342 322L382 362L342 402zM382 322L422 362L382 402zM422 322L462 362L422 402z" fill={cream} opacity="0.7" />
        <path d="M572 128H696M572 150H696M572 172H696" stroke={green} strokeWidth="12" />
      </Box>
    </Box>
  );
}
