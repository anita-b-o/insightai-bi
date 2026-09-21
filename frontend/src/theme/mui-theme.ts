import { alpha, createTheme } from "@mui/material/styles";

import { tokens } from "./tokens";

export const nextAppTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: tokens.color.accent.deepGreen,
      contrastText: tokens.color.fg.inverse,
    },
    secondary: {
      main: tokens.color.fg.primary,
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
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontWeightMedium: 650,
    fontWeightBold: 750,
    h1: { fontSize: "clamp(2rem, 5vw, 3.75rem)", fontWeight: 690, lineHeight: 1.02, letterSpacing: "-0.045em" },
    h2: { fontSize: "2.25rem", fontWeight: 700, lineHeight: 1.08, letterSpacing: "-0.035em" },
    h3: { fontSize: "1.875rem", fontWeight: 700, lineHeight: 1.12, letterSpacing: "-0.03em" },
    h4: { fontSize: "1.5rem", fontWeight: 700, lineHeight: 1.18, letterSpacing: "-0.025em" },
    h5: { fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.24, letterSpacing: "-0.02em" },
    h6: { fontSize: "1rem", fontWeight: 750, lineHeight: 1.3, letterSpacing: "-0.012em" },
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
          backgroundImage: "none",
          fontFeatureSettings: '"kern"',
        },
        "code, pre, kbd, samp": {
          fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
        },
        "*:focus-visible": {
          outline: `3px solid ${tokens.color.accent.signal}`,
          outlineOffset: 2,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.color.bg.surface,
          backdropFilter: "none",
          borderBottom: `1px solid ${tokens.color.border.subtle}`,
          boxShadow: "none",
          color: tokens.color.fg.primary,
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
          minHeight: tokens.layout.controlStandard,
          borderRadius: tokens.radius.sm,
          paddingInline: 13,
          boxShadow: "none",
          borderWidth: 1,
          "&:focus-visible": {
            outline: `3px solid ${tokens.color.accent.signal}`,
            outlineOffset: 2,
          },
        },
        contained: {
          boxShadow: "none",
        },
        containedPrimary: {
          background: tokens.color.accent.deepGreen,
          color: tokens.color.fg.inverse,
          "&:hover": {
            background: "#074C42",
          },
        },
        outlined: {
          borderColor: tokens.color.border.strong,
          backgroundColor: tokens.color.bg.surface,
          color: tokens.color.accent.deepGreen,
          "&:hover": {
            borderColor: tokens.color.fg.primary,
            backgroundColor: tokens.color.bg.surfaceMuted,
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
    MuiDialog: {
      styleOverrides: {
        paper: { border: `1px solid ${tokens.color.border.strong}`, borderRadius: tokens.radius.md, boxShadow: "none" },
      },
    },
    MuiTableRow: {
      styleOverrides: { root: { "&.MuiTableRow-hover:hover": { backgroundColor: "#F8F8F4" } } },
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
            borderColor: tokens.color.accent.signal,
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
