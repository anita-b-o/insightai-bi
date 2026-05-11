import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { DataTableFrame } from "@next/components/ui/data-table";
import { SectionBand } from "@next/components/ui/surface-card";
import { tokens } from "@next/theme/tokens";

import type { DemoDatasetPreview } from "../types";

export function DemoDatasetPreview({ dataset }: { dataset: DemoDatasetPreview }) {
  return (
    <SectionBand
      eyebrow="Demo dataset"
      title="Context before the first question"
      description={dataset.description}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "1.2fr 0.8fr" },
          gap: 3,
          alignItems: "start",
        }}
      >
        <DataTableFrame>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(140px, 1fr) minmax(120px, 0.7fr) minmax(220px, 1.6fr)",
              minWidth: 640,
            }}
          >
            <HeaderCell>Field</HeaderCell>
            <HeaderCell>Type</HeaderCell>
            <HeaderCell>Description</HeaderCell>
            {dataset.columns.map((column) => (
              <Box key={column.name} sx={{ display: "contents" }}>
                <BodyCell strong>{column.name}</BodyCell>
                <BodyCell>{column.type}</BodyCell>
                <BodyCell>{column.description}</BodyCell>
              </Box>
            ))}
          </Box>
        </DataTableFrame>

        <Stack
          spacing={1.4}
          sx={{
            pl: { lg: 2 },
            borderLeft: { lg: `1px solid ${alpha(tokens.color.border.strong, 0.38)}` },
          }}
        >
          <Typography variant="subtitle2">Suggested Ask AI prompts</Typography>
          <Stack component="ul" spacing={0.85} sx={{ m: 0, pl: 2.2 }}>
            {dataset.sampleQuestions.map((question) => (
              <Typography key={question} component="li" variant="body2" color="text.secondary">
                {question}
              </Typography>
            ))}
          </Stack>
        </Stack>
      </Box>
    </SectionBand>
  );
}

function HeaderCell({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        px: 1.5,
        py: 1.05,
        borderBottom: `1px solid ${alpha(tokens.color.border.strong, 0.82)}`,
        backgroundColor: alpha(tokens.color.bg.surfaceMuted, 0.96),
      }}
    >
      <Typography variant="caption" sx={{ color: tokens.color.fg.secondary, fontWeight: 700, letterSpacing: "0.03em" }}>
        {children}
      </Typography>
    </Box>
  );
}

function BodyCell({ children, strong = false }: { children: ReactNode; strong?: boolean }) {
  return (
    <Box
      sx={{
        px: 1.5,
        py: 1.15,
        borderBottom: `1px solid ${alpha(tokens.color.border.subtle, 0.74)}`,
        backgroundColor: alpha(tokens.color.bg.surface, 0.92),
      }}
    >
      <Typography variant="body2" color={strong ? "text.primary" : "text.secondary"} sx={{ fontWeight: strong ? 600 : 400 }}>
        {children}
      </Typography>
    </Box>
  );
}
