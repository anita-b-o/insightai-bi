import { Stack, Typography } from "@mui/material";

import { AIResultView } from "@next/features/ai/components/ai-result-view";
import { SectionBand } from "@next/components/ui/surface-card";
import { InsightCard } from "@next/features/insights/components/insight-card";

import type { DemoExperience } from "../types";

export function DemoAIShowcase({ demo }: { demo: DemoExperience }) {
  return (
    <Stack spacing={4}>
      <SectionBand
        eyebrow="Ask AI"
        title="SQL-backed answer preview"
        description="A focused example showing the answer first, then the visualization and supporting result."
      >
        <Stack spacing={1.5}>
          <Typography variant="h5">Ask AI</Typography>
          <AIResultView result={demo.askAIResult} />
        </Stack>
      </SectionBand>

      <SectionBand
        eyebrow="Insight narrative"
        title="What the insight engine surfaced"
        description={demo.insightNarrative.summary}
      >
        <Stack spacing={2}>
          <Typography variant="h4">Top insights</Typography>
          {demo.insights.slice(0, 1).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </Stack>
      </SectionBand>
    </Stack>
  );
}
