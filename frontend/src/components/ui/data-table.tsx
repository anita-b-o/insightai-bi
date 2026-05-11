import type { PropsWithChildren } from "react";
import { alpha } from "@mui/material/styles";
import { Box, TableContainer } from "@mui/material";

import { tokens } from "@next/theme/tokens";

export function DataTableFrame({
  children,
  maxHeight,
}: PropsWithChildren<{ maxHeight?: number | string }>) {
  return (
    <TableContainer
      sx={{
        width: "100%",
        overflowX: "auto",
        maxHeight,
        overflowY: maxHeight ? "auto" : undefined,
        borderRadius: tokens.radius.xs,
        border: `1px solid ${alpha(tokens.color.border.strong, 0.56)}`,
        backgroundColor: tokens.color.bg.surface,
        boxShadow: "none",
        scrollbarWidth: "thin",
        "&::-webkit-scrollbar": {
          width: 8,
          height: 8,
        },
        "&::-webkit-scrollbar-thumb": {
          backgroundColor: alpha(tokens.color.fg.primary, 0.14),
          borderRadius: tokens.radius.xs,
        },
      }}
    >
      {children}
    </TableContainer>
  );
}

export function TableSectionDivider() {
  return (
    <Box
      sx={{
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.4)}`,
      }}
    />
  );
}
