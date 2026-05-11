import { Stack } from "@mui/material";

import { PageSurface } from "@next/components/ui/page-surface";
import { DemoAIShowcase } from "@next/features/demo/components/demo-ai-showcase";
import { DemoDashboardPreview } from "@next/features/demo/components/demo-dashboard-preview";
import { DemoDatasetPreview } from "@next/features/demo/components/demo-dataset-preview";
import { DemoHero } from "@next/features/demo/components/demo-hero";
import { useDemoExperience } from "@next/features/demo/hooks";

export function NextDemoPage() {
  const demo = useDemoExperience();

  return (
    <PageSurface variant="workspace">
      <Stack spacing={5}>
        <DemoHero demo={demo} />
        <DemoDatasetPreview dataset={demo.dataset} />
        <DemoAIShowcase demo={demo} />
        <DemoDashboardPreview demo={demo} />
      </Stack>
    </PageSurface>
  );
}
