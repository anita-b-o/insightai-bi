import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { isAxiosError } from "axios";

import {
  getCurrentUser,
  login,
  register,
} from "@next/core/api/auth";
import { reportClientError } from "@next/app/client-error-reporting";
import { toApiError } from "@next/core/api/errors";
import type { LoginPayload, RegisterPayload, SessionUser } from "@next/core/types/auth";
import {
  AUTH_SESSION_INVALIDATED_EVENT,
  clearStoredToken,
  getStoredToken,
  invalidateStoredToken,
  setStoredToken,
} from "./storage";

const DEFAULT_AUTH_RESTORE_TIMEOUT_MS = 12_000;

function readRestoreTimeout(): number {
  const configuredTimeout = Number(import.meta.env.VITE_AUTH_RESTORE_TIMEOUT_MS);
  return Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : DEFAULT_AUTH_RESTORE_TIMEOUT_MS;
}

export const AUTH_RESTORE_TIMEOUT_MS = readRestoreTimeout();

export interface SessionRestoreError {
  kind: "network" | "server" | "timeout" | "unexpected";
  message: string;
  status: number | null;
  requestId: string | null;
}

interface AuthSession {
  token: string | null;
  user: SessionUser | null;
  error: SessionRestoreError | null;
}

class AuthRestoreTimeoutError extends Error {
  constructor() {
    super("The session validation request timed out.");
    this.name = "AuthRestoreTimeoutError";
  }
}

class AuthRestoreCancelledError extends Error {
  constructor() {
    super("Session restoration was cancelled.");
    this.name = "AuthRestoreCancelledError";
  }
}

interface SessionContextValue {
  user: SessionUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  restoreError: SessionRestoreError | null;
  loginUser: (payload: LoginPayload) => Promise<void>;
  registerUser: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  retrySession: () => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

async function getCurrentUserWithDeadline(signal?: AbortSignal): Promise<SessionUser> {
  const requestController = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let removeExternalAbortListener: (() => void) | undefined;

  const deadline = new Promise<never>((_, reject) => {
    const cancel = () => {
      reject(new AuthRestoreCancelledError());
      requestController.abort();
    };

    if (signal?.aborted) {
      cancel();
      return;
    }

    if (signal) {
      signal.addEventListener("abort", cancel, { once: true });
      removeExternalAbortListener = () => signal.removeEventListener("abort", cancel);
    }

    timeoutId = setTimeout(() => {
      reject(new AuthRestoreTimeoutError());
      requestController.abort();
    }, AUTH_RESTORE_TIMEOUT_MS);
  });

  try {
    return await Promise.race([
      getCurrentUser({
        signal: requestController.signal,
        timeout: AUTH_RESTORE_TIMEOUT_MS,
      }),
      deadline,
    ]);
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
    removeExternalAbortListener?.();
  }
}

function classifyRestoreError(error: unknown): SessionRestoreError {
  const apiError = toApiError(error, "The saved session could not be validated.");

  if (
    error instanceof AuthRestoreTimeoutError ||
    (isAxiosError(error) && (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT"))
  ) {
    return {
      kind: "timeout",
      message: "The server took too long to validate the saved session.",
      status: apiError.status,
      requestId: apiError.requestId,
    };
  }

  if (apiError.status !== null && apiError.status >= 500) {
    return {
      kind: "server",
      message: "The server could not validate the saved session.",
      status: apiError.status,
      requestId: apiError.requestId,
    };
  }

  if (isAxiosError(error) && !error.response) {
    return {
      kind: "network",
      message: "The server is currently unreachable. Check your connection and try again.",
      status: null,
      requestId: null,
    };
  }

  return {
    kind: "unexpected",
    message: apiError.message,
    status: apiError.status,
    requestId: apiError.requestId,
  };
}

function isRejectedSession(error: unknown): boolean {
  const status = toApiError(error).status;
  return status === 401 || status === 403;
}

export async function bootstrapAuthSession(signal?: AbortSignal): Promise<AuthSession> {
  const currentToken = getStoredToken();
  if (!currentToken) {
    return { token: null, user: null, error: null };
  }

  try {
    const currentUser = await getCurrentUserWithDeadline(signal);
    return { token: currentToken, user: currentUser, error: null };
  } catch (error: unknown) {
    if (error instanceof AuthRestoreCancelledError || signal?.aborted) {
      throw error;
    }

    if (isRejectedSession(error)) {
      invalidateStoredToken(currentToken);
      void reportClientError({
        category: "auth_session_rejected",
        message: "Stored session was rejected by the server",
        status: toApiError(error).status,
      });
      return { token: null, user: null, error: null };
    }

    const restoreError = classifyRestoreError(error);
    void reportClientError({
      category: "auth_bootstrap_failed",
      message: restoreError.message,
      requestId: restoreError.requestId,
      status: restoreError.status,
      metadata: { kind: restoreError.kind },
    });
    return { token: currentToken, user: null, error: restoreError };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<SessionUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [restoreError, setRestoreError] = useState<SessionRestoreError | null>(null);
  const restoreAttempt = useRef(0);
  const restoreController = useRef<AbortController | null>(null);

  const restoreSession = useCallback(() => {
    const attempt = restoreAttempt.current + 1;
    restoreAttempt.current = attempt;
    restoreController.current?.abort();
    const controller = new AbortController();
    restoreController.current = controller;

    setIsLoading(true);
    setRestoreError(null);

    async function bootstrap() {
      try {
        const session = await bootstrapAuthSession(controller.signal);
        if (restoreAttempt.current !== attempt || controller.signal.aborted) {
          return;
        }
        setToken(session.token);
        setUser(session.user);
        setRestoreError(session.error);
      } catch (error: unknown) {
        if (!controller.signal.aborted && restoreAttempt.current === attempt) {
          const unexpectedError = classifyRestoreError(error);
          setUser(null);
          setRestoreError(unexpectedError);
          void reportClientError({
            category: "auth_bootstrap_unexpected_failure",
            message: unexpectedError.message,
            status: unexpectedError.status,
          });
        }
      } finally {
        if (restoreAttempt.current === attempt && !controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();
  }, []);

  useEffect(() => {
    restoreSession();
    return () => {
      restoreController.current?.abort();
    };
  }, [restoreSession]);

  useEffect(() => {
    const handleInvalidatedSession = () => {
      restoreAttempt.current += 1;
      restoreController.current?.abort();
      setToken(null);
      setUser(null);
      setRestoreError(null);
      setIsLoading(false);
    };

    globalThis.addEventListener(AUTH_SESSION_INVALIDATED_EVENT, handleInvalidatedSession);
    return () => {
      globalThis.removeEventListener(AUTH_SESSION_INVALIDATED_EVENT, handleInvalidatedSession);
    };
  }, []);

  async function loginUser(payload: LoginPayload) {
    const response = await login(payload);
    setStoredToken(response.access_token);
    setToken(response.access_token);
    setRestoreError(null);

    try {
      const currentUser = await getCurrentUserWithDeadline();
      setUser(currentUser);
    } catch (error: unknown) {
      setUser(null);
      if (isRejectedSession(error)) {
        invalidateStoredToken(response.access_token);
        setToken(null);
        setRestoreError(null);
      } else {
        const validationError = classifyRestoreError(error);
        setRestoreError(validationError);
        void reportClientError({
          category: "auth_login_session_validation_failed",
          message: validationError.message,
          requestId: validationError.requestId,
          status: validationError.status,
          metadata: { kind: validationError.kind },
        });
      }
      throw error;
    }
  }

  async function registerUser(payload: RegisterPayload) {
    await register(payload);
    await loginUser({ email: payload.email, password: payload.password });
  }

  function logout() {
    restoreAttempt.current += 1;
    restoreController.current?.abort();
    clearStoredToken();
    setToken(null);
    setUser(null);
    setRestoreError(null);
    setIsLoading(false);
  }

  return (
    <SessionContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(token && user),
        isLoading,
        restoreError,
        loginUser,
        registerUser,
        logout,
        retrySession: restoreSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
