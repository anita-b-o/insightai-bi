import { Button, Link, Stack, Typography } from "@mui/material";
import type { Location } from "react-router-dom";
import { Link as RouterLink, Navigate, useLocation, useNavigate } from "react-router-dom";

import { SurfaceCard } from "@next/components/ui/surface-card";
import { useAuth } from "@next/core/auth/session";
import { NextAuthForm } from "@next/features/auth/components/auth-form";
import { NextAuthLayout } from "@next/layouts/auth-layout";

function getRedirectPath(state: unknown): string {
  const from = (state as { from?: Location } | null)?.from;
  return from?.pathname ?? "/datasets";
}

export function NextRegisterPage() {
  const { isAuthenticated, registerUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = getRedirectPath(location.state);

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <NextAuthLayout>
      <SurfaceCard
        title="Create account"
        subtitle="Register a workspace user to start profiling datasets, asking questions, and building shareable dashboards."
        padding="md"
        tone="panel"
      >
        <NextAuthForm
          mode="register"
          onSubmit={async ({ full_name, email, password }) => {
            await registerUser({ full_name: full_name ?? "", email, password });
            navigate(redirectTo, { replace: true });
          }}
        />
        <Stack spacing={1}>
          <Typography variant="body2">
            Already registered? <Link component={RouterLink} to="/login">Sign in</Link>
          </Typography>
          <Button component={RouterLink} to="/demo" variant="outlined">
            Try demo
          </Button>
        </Stack>
      </SurfaceCard>
    </NextAuthLayout>
  );
}
