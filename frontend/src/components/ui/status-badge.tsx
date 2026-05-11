import { alpha } from "@mui/material/styles";
import { Chip } from "@mui/material";

import { tokens } from "@next/theme/tokens";

type Tone = "success" | "warning" | "error" | "info";

const toneMap = {
  success: { bg: tokens.color.status.successBg, fg: tokens.color.status.successFg },
  warning: { bg: tokens.color.status.warningBg, fg: tokens.color.status.warningFg },
  error: { bg: tokens.color.status.errorBg, fg: tokens.color.status.errorFg },
  info: { bg: tokens.color.status.infoBg, fg: tokens.color.status.infoFg },
} as const;

export function StatusBadge({ label, tone }: { label: string; tone: Tone }) {
  const styles = toneMap[tone];
  return (
    <Chip
      size="small"
      label={label}
      sx={{
        backgroundColor: styles.bg,
        color: styles.fg,
        border: `1px solid ${alpha(styles.fg, 0.14)}`,
      }}
    />
  );
}
