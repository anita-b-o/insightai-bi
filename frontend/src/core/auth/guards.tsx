import type { PropsWithChildren } from "react";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
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

function SessionRestoreFailure({
  message,
  onRetry,
  onLogout,
}: {
  message: string;
  onRetry: () => void;
  onLogout: () => void;
}) {
  return (
    <Box
      display="flex"
      minHeight="100dvh"
      alignItems="center"
      justifyContent="center"
      sx={{ backgroundColor: tokens.color.bg.canvas, px: 2 }}
    >
      <Stack
        spacing={2}
        sx={{
          width: "min(520px, 100%)",
          px: 2.5,
          py: 2.25,
          borderRadius: tokens.radius.md,
          border: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
          backgroundColor: tokens.color.bg.surface,
        }}
      >
        <Typography variant="h5">Session validation unavailable</Typography>
        <Alert severity="warning">{message}</Alert>
        <Typography variant="body2" color="text.secondary">
          Your saved session was kept because the server did not reject it. You can try once more or return to sign in.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button variant="contained" onClick={onRetry}>
            Try again
          </Button>
          <Button variant="outlined" onClick={onLogout}>
            Back to sign in
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}

export function AuthGuard({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading, logout, restoreError, retrySession } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (restoreError) {
    return <SessionRestoreFailure message={restoreError.message} onRetry={retrySession} onLogout={logout} />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}

export function GuestGuard({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading, logout, restoreError, retrySession } = useAuth();
  const location = useLocation();
  const redirectPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/datasets";

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (restoreError) {
    return <SessionRestoreFailure message={restoreError.message} onRetry={retrySession} onLogout={logout} />;
  }

  if (isAuthenticated) {
    return <Navigate to={redirectPath} replace />;
  }

  return <>{children}</>;
}
