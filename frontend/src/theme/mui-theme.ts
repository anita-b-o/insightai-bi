import { alpha, createTheme } from "@mui/material/styles";

import { tokens } from "./tokens";

export const nextAppTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: tokens.color.accent.orange,
      contrastText: tokens.color.fg.inverse,
    },
    secondary: {
      main: tokens.color.accent.deepGreen,
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
    fontFamily: '"Aptos", "Inter", "Segoe UI", system-ui, sans-serif',
    fontWeightMedium: 650,
    fontWeightBold: 780,
    h1: { fontSize: "2.75rem", fontWeight: 800, lineHeight: 1.06, letterSpacing: 0 },
    h2: { fontSize: "2.25rem", fontWeight: 800, lineHeight: 1.08, letterSpacing: 0 },
    h3: { fontSize: "1.875rem", fontWeight: 800, lineHeight: 1.12, letterSpacing: 0 },
    h4: { fontSize: "1.5rem", fontWeight: 780, lineHeight: 1.18, letterSpacing: 0 },
    h5: { fontSize: "1.25rem", fontWeight: 760, lineHeight: 1.24, letterSpacing: 0 },
    h6: { fontSize: "1rem", fontWeight: 760, lineHeight: 1.3, letterSpacing: 0 },
    body1: { fontSize: "0.95rem", lineHeight: 1.58 },
    body2: { fontSize: "0.875rem", lineHeight: 1.52 },
    subtitle1: { fontWeight: 600, lineHeight: 1.4 },
    subtitle2: { fontWeight: 600, lineHeight: 1.38 },
    caption: { lineHeight: 1.45, letterSpacing: "0.01em" },
    overline: { lineHeight: 1.45, letterSpacing: "0.08em", fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 720, letterSpacing: 0 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: tokens.color.bg.canvas,
          color: tokens.color.fg.primary,
          backgroundImage: `radial-gradient(${alpha(tokens.color.fg.primary, 0.055)} 0.7px, transparent 0.7px)`,
          backgroundSize: "14px 14px",
          fontFeatureSettings: '"kern"',
        },
        "code, pre, kbd, samp": {
          fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
        },
        "*:focus-visible": {
          outline: `3px solid ${alpha(tokens.color.accent.signal, 0.86)}`,
          outlineOffset: 2,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.color.bg.inverse,
          backdropFilter: "none",
          borderBottom: `1px solid ${alpha(tokens.color.bg.surface, 0.18)}`,
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
          border: `1px solid ${alpha(tokens.color.border.strong, 0.44)}`,
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
          borderWidth: 1,
          "&:focus-visible": {
            outline: `3px solid ${alpha(tokens.color.accent.signal, 0.86)}`,
            outlineOffset: 2,
          },
        },
        contained: {
          boxShadow: "none",
        },
        containedPrimary: {
          background: tokens.color.accent.orange,
          color: tokens.color.fg.inverse,
          "&:hover": {
            background: tokens.color.accent.terracotta,
          },
        },
        outlined: {
          borderColor: alpha(tokens.color.accent.deepGreen, 0.34),
          backgroundColor: tokens.color.bg.surface,
          color: tokens.color.accent.deepGreen,
          "&:hover": {
            borderColor: alpha(tokens.color.accent.deepGreen, 0.58),
            backgroundColor: alpha(tokens.color.accent.deepGreen, 0.05),
          },
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
          backgroundColor: tokens.color.bg.surface,
          "& .MuiOutlinedInput-notchedOutline": {
            borderColor: alpha(tokens.color.border.strong, 0.66),
          },
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: alpha(tokens.color.accent.deepGreen, 0.64),
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: tokens.color.accent.deepGreen,
            borderWidth: 2,
          },
        },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: alpha(tokens.color.border.strong, 0.22),
        },
      },
    },
  },
});
