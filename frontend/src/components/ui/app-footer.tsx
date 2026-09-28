import { Box, Link, Typography } from "@mui/material";

import { tokens } from "@next/theme/tokens";

export function AppFooter() {
  return (
    <Box
      component="footer"
      sx={{
        width: "100%",
        maxWidth: tokens.layout.appMaxWidth,
        mx: "auto",
        px: { xs: 2, md: 3.25 },
        py: { xs: 2, md: 2.5 },
        textAlign: "center",
      }}
    >
      <Typography variant="caption" color="text.secondary">
        Developed by{" "}
        <Link
          href="https://pampasoftware.com.ar/"
          target="_blank"
          rel="noopener noreferrer"
          color="secondary.main"
          underline="none"
          sx={{
            fontWeight: "medium",
            "&:hover, &:focus-visible": {
              textDecoration: "underline",
              textUnderlineOffset: "0.18em",
            },
          }}
        >
          Pampa Software
        </Link>
      </Typography>
    </Box>
  );
}
