import type { PropsWithChildren } from "react";
import { alpha } from "@mui/material/styles";
import { Stack } from "@mui/material";

import { tokens } from "@next/theme/tokens";

export function Toolbar({ children }: PropsWithChildren) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1.25}
      useFlexGap
      flexWrap="wrap"
      alignItems={{ xs: "stretch", sm: "center" }}
      sx={{
        p: 1,
        borderRadius: 0,
        border: `1px solid ${tokens.color.border.subtle}`,
        backgroundColor: tokens.color.bg.surface,
      }}
    >
      {children}
    </Stack>
  );
}
