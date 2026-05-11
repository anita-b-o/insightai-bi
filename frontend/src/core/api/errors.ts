import { isAxiosError, type AxiosError } from "axios";

export interface ApiFieldError {
  field: string;
  message: string;
}

export interface ApiError {
  message: string;
  status: number | null;
  requestId: string | null;
  fieldErrors: ApiFieldError[];
}

interface ValidationErrorItem {
  loc?: unknown;
  msg?: unknown;
}

interface ApiErrorPayload {
  detail?: unknown;
}

function getAxiosResponse(error: unknown): AxiosError<ApiErrorPayload>["response"] | null {
  if (!isAxiosError<ApiErrorPayload>(error)) {
    if (error && typeof error === "object" && "response" in error) {
      return (error as { response?: AxiosError<ApiErrorPayload>["response"] }).response ?? null;
    }
    return null;
  }
  return error.response ?? null;
}

export function toApiError(error: unknown, fallback = "Request failed"): ApiError {
  const response = getAxiosResponse(error);
  const detail = response?.data?.detail;
  const requestId = response?.headers?.["x-request-id"] ?? null;

  if (typeof detail === "string" && detail.trim()) {
    return {
      message: detail,
      status: response?.status ?? null,
      requestId,
      fieldErrors: [],
    };
  }

  if (Array.isArray(detail)) {
    const fieldErrors = detail
      .map((item) => {
        const candidate = item as ValidationErrorItem | null;
        if (!item || typeof item !== "object") {
          return null;
        }
        const field = Array.isArray(candidate?.loc) ? candidate.loc.slice(1).join(".") : "";
        const message = typeof candidate?.msg === "string" ? candidate.msg : null;
        if (!message) {
          return null;
        }
        return { field, message };
      })
      .filter((item): item is ApiFieldError => Boolean(item));

    return {
      message: fieldErrors[0]?.message ?? fallback,
      status: response?.status ?? null,
      requestId,
      fieldErrors,
    };
  }

  return {
    message: error instanceof Error && error.message ? error.message : fallback,
    status: response?.status ?? null,
    requestId,
    fieldErrors: [],
  };
}

export function getApiErrorMessage(error: unknown, fallback = "Request failed"): string {
  return toApiError(error, fallback).message;
}
