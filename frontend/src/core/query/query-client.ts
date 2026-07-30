import { QueryClient } from "@tanstack/react-query";

import { toApiError } from "@next/core/api/errors";

export const nextQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        const status = toApiError(error).status;
        return status !== 401 && status !== 403 && failureCount < 1;
      },
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
    mutations: {
      retry: 0,
    },
  },
});
