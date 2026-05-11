import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getApiErrorMessage } from "@next/core/api/errors";
import { nextQueryKeys } from "@next/core/query/query-keys";

import {
  deleteAIQueryHistory,
  getAIQueryHistoryDetail,
  listAIQueryHistory,
  queryDatasetWithAI,
  updateAIQueryHistory,
} from "./api";
import type { AIQueryHistoryUpdatePayload } from "./types";

export function useAIQueryHistory(datasetId: number) {
  return useQuery({
    queryKey: nextQueryKeys.ai.history(datasetId),
    queryFn: () => listAIQueryHistory(datasetId),
  });
}

export function useAIQueryHistoryDetail(queryId: number | null) {
  return useQuery({
    queryKey: queryId ? nextQueryKeys.ai.historyDetail(queryId) : ["ai", "history", "detail", "missing"],
    queryFn: () => getAIQueryHistoryDetail(queryId!),
    enabled: typeof queryId === "number" && Number.isFinite(queryId),
  });
}

export function useAskAIMutation(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (question: string) => queryDatasetWithAI(datasetId, question),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.ai.history(datasetId) });
      if (result.query_id) {
        await queryClient.invalidateQueries({ queryKey: nextQueryKeys.ai.historyDetail(result.query_id) });
      }
    },
    meta: { errorMessage: "Could not query the dataset with AI" },
  });
}

export function useUpdateAIQueryHistoryMutation(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ queryId, payload }: { queryId: number; payload: AIQueryHistoryUpdatePayload }) =>
      updateAIQueryHistory(queryId, payload),
    onSuccess: async (detail) => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.ai.history(datasetId) });
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.ai.historyDetail(detail.id) });
    },
    meta: { errorMessage: "Could not update query history" },
  });
}

export function useDeleteAIQueryHistoryMutation(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (queryId: number) => deleteAIQueryHistory(queryId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: nextQueryKeys.ai.history(datasetId) });
    },
    meta: { errorMessage: "Could not delete query history" },
  });
}

export function getMutationErrorMessage(error: unknown, fallback: string) {
  return getApiErrorMessage(error, fallback);
}
