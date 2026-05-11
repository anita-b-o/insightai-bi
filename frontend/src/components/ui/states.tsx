import type { ReactNode } from "react";
import { Alert, AlertTitle, Box, Button, Skeleton, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { SurfaceCard } from "./surface-card";
import { tokens } from "@next/theme/tokens";

export function LoadingState({
  title = "Loading",
  description = "Fetching data from the API.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <SurfaceCard tone="panel" padding="md">
      <Stack spacing={1.4}>
        <Stack spacing={0.7}>
          <Typography variant="overline" color="text.secondary">
            Loading
          </Typography>
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        </Stack>
        <Skeleton variant="rounded" height={12} width="28%" />
        <Skeleton variant="rounded" height={16} />
        <Skeleton variant="rounded" height={16} width="82%" />
        <Skeleton variant="rounded" height={140} sx={{ borderRadius: tokens.radius.sm }} />
      </Stack>
    </SurfaceCard>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <SurfaceCard tone="panel" padding="md">
      <Stack spacing={1.15}>
        <Typography variant="overline" color="text.secondary">
          Empty state
        </Typography>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 680 }}>
          {description}
        </Typography>
        {action ? (
          <Box
            sx={{
              pt: 0.5,
              borderTop: `1px solid ${alpha(tokens.color.border.strong, 0.24)}`,
            }}
          >
            {action}
          </Box>
        ) : null}
      </Stack>
    </SurfaceCard>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <SurfaceCard tone="panel" padding="sm">
      <Alert
        severity="error"
        variant="outlined"
        role="alert"
        action={
          onRetry ? (
            <Button color="inherit" size="small" onClick={onRetry}>
              Retry
            </Button>
          ) : undefined
        }
      >
        <AlertTitle>{title}</AlertTitle>
        {description}
      </Alert>
    </SurfaceCard>
  );
}

export function InlineHint({ children }: { children: ReactNode }) {
  return (
    <Stack spacing={0.5} role="note">
      <Typography variant="body2" color="text.secondary">
        {children}
      </Typography>
    </Stack>
  );
}
