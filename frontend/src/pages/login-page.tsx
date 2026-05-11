import { Button, Link, Stack, Typography } from "@mui/material";
import { Link as RouterLink, Navigate, useLocation, useNavigate } from "react-router-dom";

import { SurfaceCard } from "@next/components/ui/surface-card";
import { useAuth } from "@next/core/auth/session";
import { NextAuthForm } from "@next/features/auth/components/auth-form";
import { NextAuthLayout } from "@next/layouts/auth-layout";

function getRedirectPath(state: unknown): string {
  if (
    state &&
    typeof state === "object" &&
    "from" in state &&
    state.from &&
    typeof state.from === "object" &&
    "pathname" in state.from &&
    typeof state.from.pathname === "string"
  ) {
    return state.from.pathname;
  }

  return "/datasets";
}

export function NextLoginPage() {
  const { isAuthenticated, loginUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = getRedirectPath(location.state);

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <NextAuthLayout>
      <SurfaceCard
        title="Sign in"
        subtitle="Access datasets, Ask AI workflows, and persistent dashboards from a single analytics workspace."
        padding="md"
      >
        <NextAuthForm
          mode="login"
          onSubmit={async ({ email, password }) => {
            await loginUser({ email, password });
            navigate(redirectTo, { replace: true });
          }}
        />
        <Stack spacing={1}>
          <Typography variant="body2">
            No account yet? <Link component={RouterLink} to="/register">Create one</Link>
          </Typography>
          <Button component={RouterLink} to="/demo" variant="outlined">
            Try demo
          </Button>
        </Stack>
      </SurfaceCard>
    </NextAuthLayout>
  );
}
