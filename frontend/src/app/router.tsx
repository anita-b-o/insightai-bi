import { Box, CircularProgress, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";

import { AuthGuard, GuestGuard } from "@next/core/auth/guards";
import { NextAppShell } from "@next/layouts/app-shell";
import { NextPublicLayout } from "@next/layouts/public-layout";
import { tokens } from "@next/theme/tokens";

const DemoPage = lazy(() => import("@next/pages/demo-page").then((module) => ({ default: module.NextDemoPage })));
const DashboardDetailPage = lazy(() =>
  import("@next/pages/dashboard-detail-page").then((module) => ({ default: module.NextDashboardDetailPage })),
);
const DashboardsPage = lazy(() =>
  import("@next/pages/dashboards-page").then((module) => ({ default: module.NextDashboardsPage })),
);
const DatasetDetailPage = lazy(() =>
  import("@next/pages/dataset-detail-page").then((module) => ({ default: module.NextDatasetDetailPage })),
);
const DatasetsPage = lazy(() =>
  import("@next/pages/datasets-page").then((module) => ({ default: module.NextDatasetsPage })),
);
const LoginPage = lazy(() => import("@next/pages/login-page").then((module) => ({ default: module.NextLoginPage })));
const NotFoundPage = lazy(() =>
  import("@next/pages/not-found-page").then((module) => ({ default: module.NextNotFoundPage })),
);
const RegisterPage = lazy(() =>
  import("@next/pages/register-page").then((module) => ({ default: module.NextRegisterPage })),
);
const SharedDashboardPage = lazy(() =>
  import("@next/pages/shared-dashboard-page").then((module) => ({ default: module.NextSharedDashboardPage })),
);
const UploadDatasetPage = lazy(() =>
  import("@next/pages/upload-page").then((module) => ({ default: module.NextUploadPage })),
);

function RouterFallback() {
  const location = useLocation();
  const isAuthRoute = location.pathname === "/login" || location.pathname === "/register";
  const isPublicRoute = location.pathname.startsWith("/share/") || location.pathname === "/demo";

  if (isAuthRoute || isPublicRoute) {
    return (
      <Box
        sx={{
          minHeight: "100dvh",
          display: "grid",
          placeItems: "center",
          px: 2,
          backgroundColor: tokens.color.bg.canvas,
        }}
      >
        <Stack
          spacing={1.2}
          sx={{
            width: "min(720px, 100%)",
            px: { xs: 2.4, md: 3 },
            py: { xs: 2.5, md: 3 },
            borderRadius: 2,
            border: `1px solid ${alpha(tokens.color.border.strong, 0.3)}`,
            backgroundColor: tokens.color.bg.surface,
            boxShadow: tokens.shadow.sm,
          }}
        >
          <Typography variant="overline" color="text.secondary">
            InsightAI BI
          </Typography>
          <Typography variant="h3" sx={{ maxWidth: 640 }}>
            Loading analytics workspace
          </Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 620 }}>
            Preparing the current route, restoring session context, and resolving the next surface.
          </Typography>
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ pt: 0.35 }}>
            <CircularProgress size={20} />
            <Typography color="text.secondary">Loading page...</Typography>
          </Stack>
        </Stack>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "280px minmax(0, 1fr)" },
        backgroundColor: tokens.color.bg.canvas,
      }}
    >
      <Box
        sx={{
          display: { xs: "none", lg: "block" },
          background: `linear-gradient(180deg, ${tokens.color.bg.inverse} 0%, #122236 100%)`,
          borderRight: `1px solid ${tokens.color.border.subtle}`,
        }}
      />
      <Box sx={{ minWidth: 0 }}>
        <Box
          sx={{
            height: 72,
            px: { xs: 2, md: 3.25 },
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: tokens.color.bg.inverse,
            color: tokens.color.fg.inverse,
            borderBottom: `1px solid ${alpha(tokens.color.bg.surface, 0.08)}`,
          }}
        >
          <Stack spacing={0.15}>
            <Typography variant="subtitle1">InsightAI BI</Typography>
            <Typography variant="body2" sx={{ color: alpha(tokens.color.fg.inverse, 0.66) }}>
              Editorial analytics workspace
            </Typography>
          </Stack>
          <CircularProgress size={20} sx={{ color: tokens.color.fg.inverse }} />
        </Box>
        <Box sx={{ px: { xs: 2, md: 3.25, xl: 4 }, py: { xs: 3, md: 4.5 }, maxWidth: tokens.layout.appMaxWidth, mx: "auto" }}>
          <Stack
            spacing={1.25}
            sx={{
              px: { xs: 2.2, md: 2.6 },
              py: { xs: 2.2, md: 2.5 },
              borderRadius: tokens.radius.md,
              border: `1px solid ${alpha(tokens.color.border.strong, 0.3)}`,
              backgroundColor: tokens.color.bg.surface,
            }}
          >
            <Typography variant="overline" color="text.secondary">
              Loading workspace
            </Typography>
            <Typography variant="h4">Preparing this route</Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 720 }}>
              Resolving navigation, route modules, and the current page data without leaving the workspace blank.
            </Typography>
            <Stack direction="row" spacing={1.25} alignItems="center" sx={{ pt: 0.35 }}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">Loading page...</Typography>
            </Stack>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

function LegacyPublicDashboardRedirect() {
  const { token } = useParams();
  return <Navigate to={token ? `/share/${token}` : "/share"} replace />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouterFallback />}>
        <Routes>
          <Route
            path="/login"
            element={
              <GuestGuard>
                <LoginPage />
              </GuestGuard>
            }
          />
          <Route
            path="/register"
            element={
              <GuestGuard>
                <RegisterPage />
              </GuestGuard>
            }
          />
          <Route
            path="/demo"
            element={
              <NextPublicLayout>
                <DemoPage />
              </NextPublicLayout>
            }
          />
          <Route
            path="/share/:token"
            element={
              <NextPublicLayout>
                <SharedDashboardPage />
              </NextPublicLayout>
            }
          />
          <Route path="/public/dashboards/:token" element={<LegacyPublicDashboardRedirect />} />
          <Route
            path="/"
            element={
              <AuthGuard>
                <NextAppShell />
              </AuthGuard>
            }
          >
            <Route index element={<Navigate to="/datasets" replace />} />
            <Route path="datasets" element={<DatasetsPage />} />
            <Route path="datasets/:datasetId" element={<DatasetDetailPage />} />
            <Route path="upload" element={<UploadDatasetPage />} />
            <Route path="datasets/upload" element={<Navigate to="/upload" replace />} />
            <Route path="dashboards" element={<DashboardsPage />} />
            <Route path="dashboards/:dashboardId" element={<DashboardDetailPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
