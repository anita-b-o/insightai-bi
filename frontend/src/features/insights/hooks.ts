import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nextQueryKeys } from "@next/core/query/query-keys";

import { generateDatasetInsights, getLatestDatasetInsights, refreshDatasetInsights } from "./api";

export function useLatestDatasetInsights(datasetId: number) {
  return useQuery({
    queryKey: nextQueryKeys.datasets.insightsLatest(datasetId),
    queryFn: () => getLatestDatasetInsights(datasetId),
  });
}

export function useGenerateDatasetInsights(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (hasExisting: boolean) => (hasExisting ? refreshDatasetInsights(datasetId) : generateDatasetInsights(datasetId)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.datasets.insightsLatest(datasetId) });
    },
  });
}
