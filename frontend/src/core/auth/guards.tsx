import type { PropsWithChildren } from "react";
import { Box, CircularProgress, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./session";
import { tokens } from "@next/theme/tokens";

function FullScreenLoader() {
  return (
    <Box
      display="flex"
      minHeight="100dvh"
      alignItems="center"
      justifyContent="center"
      sx={{ backgroundColor: tokens.color.bg.canvas, px: 2 }}
    >
      <Stack
        spacing={1.1}
        alignItems="center"
        sx={{
          minWidth: 0,
          px: 2.5,
          py: 2.25,
          borderRadius: tokens.radius.md,
          border: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
          backgroundColor: tokens.color.bg.surface,
        }}
      >
        <CircularProgress size={24} />
        <Typography variant="h6">Restoring session</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", maxWidth: 320 }}>
          Loading the analytics workspace and validating your current access state.
        </Typography>
      </Stack>
    </Box>
  );
}

export function AuthGuard({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}

export function GuestGuard({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const redirectPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/datasets";

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (isAuthenticated) {
    return <Navigate to={redirectPath} replace />;
  }

  return <>{children}</>;
}
