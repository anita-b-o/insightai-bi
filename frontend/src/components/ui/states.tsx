import type { ReactNode } from "react";
import { Alert, AlertTitle, Box, Button, Skeleton, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { OpenSection, SectionBlock } from "./surface-card";
import { GeoPattern } from "@next/components/brand/geo-pattern";
import { tokens } from "@next/theme/tokens";

export function LoadingState({
  title = "Finding the signal",
  description = "Fetching data from the API.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <SectionBlock eyebrow="Loading" title={title} description={description} divider="top">
      <Stack spacing={1.25}>
        <Stack spacing={0.7}>
          <Skeleton variant="text" height={18} width="20%" />
          <Skeleton variant="text" height={24} width="42%" />
          <Skeleton variant="text" height={18} width="72%" />
        </Stack>
        <Skeleton variant="rounded" height={10} width="28%" sx={{ borderRadius: tokens.radius.xs }} />
        <Skeleton variant="rounded" height={14} sx={{ borderRadius: tokens.radius.xs }} />
        <Skeleton variant="rounded" height={14} width="82%" sx={{ borderRadius: tokens.radius.xs }} />
        <Skeleton variant="rounded" height={132} sx={{ borderRadius: tokens.radius.xs }} />
      </Stack>
    </SectionBlock>
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
    <OpenSection divider="top">
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          borderRadius: tokens.radius.lg,
          border: `1px solid ${alpha(tokens.color.border.strong, 0.34)}`,
          backgroundColor: tokens.color.bg.surface,
          px: { xs: 1.75, md: 2.15 },
          py: { xs: 1.8, md: 2.15 },
        }}
      >
        <GeoPattern density="quiet" sx={{ left: "auto", width: { xs: 160, md: 260 }, opacity: 0.18 }} />
        <Stack spacing={1.1} sx={{ position: "relative", zIndex: 1, maxWidth: 720 }}>
          <Typography variant="overline" color="text.secondary">
            Empty state
          </Typography>
          <Typography variant="h5">{title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
      {action ? (
        <Box
          sx={{
            pt: 0.25,
          }}
        >
          {action}
        </Box>
      ) : null}
        </Stack>
      </Box>
    </OpenSection>
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
    <OpenSection divider="top">
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
    </OpenSection>
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
