import { alpha, createTheme } from "@mui/material/styles";

import { tokens } from "./tokens";

export const nextAppTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: tokens.color.accent.blue,
      contrastText: tokens.color.fg.inverse,
    },
    secondary: {
      main: tokens.color.accent.cyan,
      contrastText: tokens.color.fg.inverse,
    },
    success: {
      main: tokens.color.accent.green,
    },
    warning: {
      main: tokens.color.accent.amber,
    },
    error: {
      main: tokens.color.accent.red,
    },
    background: {
      default: tokens.color.bg.canvas,
      paper: tokens.color.bg.surface,
    },
    text: {
      primary: tokens.color.fg.primary,
      secondary: tokens.color.fg.secondary,
    },
    divider: tokens.color.border.subtle,
  },
  shape: {
    borderRadius: tokens.radius.sm,
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Inter", "Segoe UI", sans-serif',
    h1: { fontSize: "2.75rem", fontWeight: 700, lineHeight: 1.08, letterSpacing: "-0.04em" },
    h2: { fontSize: "2.25rem", fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.04em" },
    h3: { fontSize: "1.875rem", fontWeight: 700, lineHeight: 1.14, letterSpacing: "-0.03em" },
    h4: { fontSize: "1.5rem", fontWeight: 700, lineHeight: 1.2, letterSpacing: "-0.025em" },
    h5: { fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.24, letterSpacing: "-0.02em" },
    h6: { fontSize: "1rem", fontWeight: 700, lineHeight: 1.3, letterSpacing: "-0.01em" },
    body1: { fontSize: "0.95rem", lineHeight: 1.58 },
    body2: { fontSize: "0.875rem", lineHeight: 1.52 },
    subtitle1: { fontWeight: 600, lineHeight: 1.4 },
    subtitle2: { fontWeight: 600, lineHeight: 1.38 },
    caption: { lineHeight: 1.45, letterSpacing: "0.01em" },
    overline: { lineHeight: 1.45, letterSpacing: "0.08em", fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 600, letterSpacing: "-0.01em" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: tokens.color.bg.canvas,
          color: tokens.color.fg.primary,
          backgroundImage: "none",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.color.bg.inverse,
          backdropFilter: "none",
          borderBottom: `1px solid ${alpha(tokens.color.bg.surface, 0.08)}`,
          boxShadow: "none",
          color: tokens.color.fg.inverse,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
        rounded: {
          borderRadius: tokens.radius.md,
        },
      },
    },
    MuiCard: {
      defaultProps: {
        elevation: 0,
      },
      styleOverrides: {
        root: {
          borderRadius: tokens.radius.sm,
          border: `1px solid ${alpha(tokens.color.border.subtle, 0.88)}`,
          boxShadow: "none",
          backgroundImage: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 40,
          borderRadius: tokens.radius.sm,
          paddingInline: 13,
          boxShadow: "none",
        },
        contained: {
          boxShadow: "none",
        },
        containedPrimary: {
          background: tokens.color.accent.blue,
        },
        outlined: {
          borderColor: alpha(tokens.color.border.strong, 0.72),
          backgroundColor: tokens.color.bg.surface,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: tokens.radius.pill,
          fontWeight: 600,
          height: 24,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: alpha(tokens.color.border.strong, 0.55),
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottomColor: alpha(tokens.color.border.subtle, 0.85),
        },
        head: {
          color: tokens.color.fg.secondary,
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          fontSize: 12,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        size: "medium",
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: tokens.radius.sm,
        },
      },
    },
  },
});
