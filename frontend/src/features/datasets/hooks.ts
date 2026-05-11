import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nextQueryKeys } from "@next/core/query/query-keys";

import { getDataset, listDatasets, uploadDataset } from "./api";

export function useDatasetsList() {
  return useQuery({
    queryKey: nextQueryKeys.datasets.list,
    queryFn: listDatasets,
  });
}

export function useDatasetDetail(datasetId: number | null) {
  return useQuery({
    queryKey: datasetId ? nextQueryKeys.datasets.detail(datasetId) : ["datasets", "detail", "missing"],
    queryFn: () => getDataset(datasetId!),
    enabled: typeof datasetId === "number" && Number.isFinite(datasetId),
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadDataset,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.datasets.list });
    },
  });
}
