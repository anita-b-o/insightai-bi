import { Button, Stack, Typography } from "@mui/material";

import { SurfaceCard } from "@next/components/ui/surface-card";

export function InsightEmptyState({
  isGenerating,
  onGenerate,
}: {
  isGenerating: boolean;
  onGenerate: () => void;
}) {
  return (
    <SurfaceCard tone="well" padding="md">
      <Stack spacing={1.25}>
        <Typography variant="h6">No insights generated yet</Typography>
        <Typography color="text.secondary">
          Run the insight engine to detect trends, top performers, outliers, and ranked findings without writing a question first.
        </Typography>
        <Stack direction="row">
          <Button variant="contained" onClick={onGenerate} disabled={isGenerating}>
            Generate insights
          </Button>
        </Stack>
      </Stack>
    </SurfaceCard>
  );
}
