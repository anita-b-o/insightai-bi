import axios, { isAxiosError } from "axios";

import { reportClientError } from "@next/app/client-error-reporting";
import { getStoredToken } from "../auth/storage";

const REQUEST_ID_HEADER = "X-Request-ID";

function createRequestId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const nextApiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
});

nextApiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  const requestId = createRequestId();

  config.headers = config.headers ?? {};
  config.headers[REQUEST_ID_HEADER] = requestId;

  if (config.data instanceof FormData) {
    delete (config.headers as Record<string, unknown>)["Content-Type"];
    delete (config.headers as Record<string, unknown>)["content-type"];
  } else if (!config.headers["Content-Type"]) {
    config.headers["Content-Type"] = "application/json";
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

nextApiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (isAxiosError(error) && error.response?.status === 401) {
      const currentToken = getStoredToken();
      if (currentToken) {
        localStorage.removeItem("insightai.bi.token");
      }
    }
    if (isAxiosError(error) && error.response?.status && error.response.status >= 500) {
      void reportClientError({
        category: "api_server_error",
        message: error.message,
        requestId: String(error.response.headers?.["x-request-id"] ?? ""),
        status: error.response.status,
        metadata: {
          method: error.config?.method,
          url: error.config?.url,
        },
      });
    }
    return Promise.reject(error);
  },
);
