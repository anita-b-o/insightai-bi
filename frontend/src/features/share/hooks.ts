import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nextQueryKeys } from "@next/core/query/query-keys";

import { createDashboardShareLink, getSharedDashboard, listDashboardShareLinks, revokeDashboardShareLink } from "./api";

export function useSharedDashboard(token: string | null) {
  return useQuery({
    queryKey: token ? nextQueryKeys.public.sharedDashboard(token) : ["public", "shared-dashboard", "missing"],
    queryFn: () => getSharedDashboard(token!),
    enabled: Boolean(token),
  });
}

export function useDashboardShareLinks(dashboardId: number, enabled: boolean) {
  return useQuery({
    queryKey: nextQueryKeys.dashboards.shareLinks(dashboardId),
    queryFn: () => listDashboardShareLinks(dashboardId),
    enabled,
  });
}

export function useCreateDashboardShareLink(dashboardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDashboardShareLink.bind(null, dashboardId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.shareLinks(dashboardId) });
    },
  });
}

export function useRevokeDashboardShareLink(dashboardId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (shareId: number) => revokeDashboardShareLink(dashboardId, shareId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.dashboards.shareLinks(dashboardId) });
    },
  });
}
