import type { PropsWithChildren } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";

import { nextAppTheme } from "@next/theme/mui-theme";

export function NextThemeBoundary({ children }: PropsWithChildren) {
  return (
    <ThemeProvider theme={nextAppTheme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
