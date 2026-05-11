import type { AIQueryResponse } from "@next/features/ai/types";
import type { DashboardDetail, DashboardNarrative, DashboardWidget } from "@next/features/dashboards/types";
import type { InsightItem, InsightNarrative } from "@next/features/insights/types";

export interface DemoDatasetPreview {
  id: number;
  name: string;
  description: string;
  rowCount: number;
  columnCount: number;
  sampleQuestions: string[];
  columns: Array<{
    name: string;
    type: string;
    description: string;
  }>;
}

export interface DemoExperience {
  dataset: DemoDatasetPreview;
  askAIResult: AIQueryResponse;
  insightNarrative: InsightNarrative;
  insights: InsightItem[];
  dashboardNarrative: DashboardNarrative;
  dashboard: DashboardDetail;
}

export type DemoWidget = DashboardWidget;
