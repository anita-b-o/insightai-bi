export const nextQueryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  datasets: {
    list: ["datasets", "list"] as const,
    detail: (datasetId: number) => ["datasets", "detail", datasetId] as const,
    insightsLatest: (datasetId: number) => ["datasets", "insights", "latest", datasetId] as const,
    insightRuns: (datasetId: number) => ["datasets", "insights", "runs", datasetId] as const,
  },
  ai: {
    history: (datasetId?: number) => ["ai", "history", datasetId ?? "all"] as const,
    historyDetail: (queryId: number) => ["ai", "history", "detail", queryId] as const,
  },
  dashboards: {
    list: ["dashboards", "list"] as const,
    detail: (dashboardId: number) => ["dashboards", "detail", dashboardId] as const,
    narrative: (dashboardId: number) => ["dashboards", "narrative", dashboardId] as const,
    shareLinks: (dashboardId: number) => ["dashboards", "share-links", dashboardId] as const,
  },
  public: {
    sharedDashboard: (token: string) => ["public", "shared-dashboard", token] as const,
  },
};
