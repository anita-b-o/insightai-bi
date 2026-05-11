import type { VisualizationSuggestion } from "@next/features/ai/types";

export interface InsightNarrative {
  summary: string;
  key_findings: string[];
  risks_or_caveats: string[];
  recommended_next_questions: string[];
}

export interface InsightItem {
  id: string;
  type: string;
  title: string;
  description: string;
  summary: string;
  severity: "info" | "warning" | "critical";
  metric: string | null;
  dimension: string | null;
  value: string | number | null;
  confidence: number;
  impact: number;
  priority: "high" | "medium" | "low";
  sql: string | null;
  chart_suggestion: "bar" | "line" | "pie" | "scatter" | "table" | null;
  chart_type: "bar" | "line" | "pie" | "scatter" | "table";
  data: Record<string, unknown>[];
  columns: string[];
  rows: Record<string, unknown>[];
  visualization_suggestion: VisualizationSuggestion | null;
}

export interface InsightsResponse {
  run_id: number | null;
  dataset_id: number;
  dataset_name: string;
  status: "success" | "failed";
  generated_at: string;
  is_stale: boolean;
  error_message: string | null;
  insights: InsightItem[];
  narrative: InsightNarrative;
}
