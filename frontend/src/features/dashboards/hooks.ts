import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nextQueryKeys } from "@next/core/query/query-keys";

import { createDashboard, getDashboard, getDashboardNarrative, listDashboards, refreshDashboard, refreshDashboardWidget } from "./api";
import type { DashboardDetail } from "./types";

export function useDashboardsList() {
  return useQuery({
    queryKey: nextQueryKeys.dashboards.list,
    queryFn: listDashboards,
  });
}

export function useCreateDashboard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDashboard,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.list });
    },
  });
}

export function useDashboardDetail(dashboardId: number | null) {
  return useQuery({
    queryKey: dashboardId ? nextQueryKeys.dashboards.detail(dashboardId) : ["dashboards", "detail", "missing"],
    queryFn: () => getDashboard(dashboardId!),
    enabled: typeof dashboardId === "number" && Number.isFinite(dashboardId),
  });
}

export function useDashboardNarrative(dashboardId: number | null) {
  return useQuery({
    queryKey: dashboardId ? nextQueryKeys.dashboards.narrative(dashboardId) : ["dashboards", "narrative", "missing"],
    queryFn: () => getDashboardNarrative(dashboardId!),
    enabled: typeof dashboardId === "number" && Number.isFinite(dashboardId),
  });
}

export function useRefreshDashboard(dashboardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => refreshDashboard(dashboardId),
    onSuccess: async (detail) => {
      queryClient.setQueryData(nextQueryKeys.dashboards.detail(dashboardId), detail);
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.list });
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.narrative(dashboardId) });
    },
  });
}

export function useRefreshDashboardWidget(dashboardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (widgetId: number) => refreshDashboardWidget(dashboardId, widgetId),
    onSuccess: async (widget) => {
      queryClient.setQueryData<DashboardDetail | undefined>(nextQueryKeys.dashboards.detail(dashboardId), (current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          widgets: current.widgets.map((item) => (item.id === widget.id ? widget : item)),
        };
      });
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.list });
    },
  });
}
