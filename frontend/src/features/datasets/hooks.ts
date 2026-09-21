import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nextQueryKeys } from "@next/core/query/query-keys";

import { deleteDataset, getDataset, listDatasets, uploadDataset } from "./api";

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

export function useDeleteDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDataset,
    onSuccess: async (_data, datasetId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: nextQueryKeys.datasets.list }),
        queryClient.removeQueries({ queryKey: nextQueryKeys.datasets.detail(datasetId) }),
      ]);
    },
  });
}
