import * as Sentry from "@sentry/react";

interface ClientErrorPayload {
  category: string;
  message: string;
  route?: string;
  requestId?: string | null;
  status?: number | null;
  metadata?: Record<string, unknown>;
}

const endpoint = import.meta.env.VITE_CLIENT_ERROR_ENDPOINT?.trim();
const sentryDsn = import.meta.env.VITE_SENTRY_DSN?.trim();
const sentryEnvironment = import.meta.env.VITE_SENTRY_ENVIRONMENT?.trim();
const tracesSampleRate = Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? "0");

function buildRoute(): string {
  return globalThis.location?.pathname ?? "unknown";
}

export async function reportClientError(payload: ClientErrorPayload): Promise<void> {
  const body = {
    ...payload,
    route: payload.route ?? buildRoute(),
    occurredAt: new Date().toISOString(),
  };

  console.error("[client_error_report]", body);

  if (sentryDsn) {
    Sentry.captureMessage(body.message, {
      level: "error",
      tags: {
        category: body.category,
        route: body.route,
        request_id: body.requestId ?? "",
      },
      extra: {
        status: body.status,
        metadata: body.metadata,
      },
    });
  }

  if (!endpoint) {
    return;
  }

  try {
    await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true,
    });
  } catch {
    // Avoid cascading failures while reporting runtime issues.
  }
}

export function initClientMonitoring(): void {
  if (!sentryDsn) {
    return;
  }

  Sentry.init({
    dsn: sentryDsn,
    environment: sentryEnvironment || "production",
    tracesSampleRate: Number.isFinite(tracesSampleRate) ? tracesSampleRate : 0,
    sendDefaultPii: false,
  });
}

export function installGlobalClientErrorHandlers(): void {
  globalThis.addEventListener("error", (event) => {
    void reportClientError({
      category: "window_error",
      message: event.message || "Unhandled browser error",
      metadata: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      },
    });
    if (sentryDsn && event.error instanceof Error) {
      Sentry.captureException(event.error);
    }
  });

  globalThis.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason instanceof Error ? event.reason.message : String(event.reason ?? "Unhandled rejection");
    void reportClientError({
      category: "unhandled_rejection",
      message: reason,
    });
    if (sentryDsn) {
      Sentry.captureException(event.reason instanceof Error ? event.reason : new Error(reason));
    }
  });
}
