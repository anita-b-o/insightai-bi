import { act, render, screen, waitFor } from "@testing-library/react";
import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_RESTORE_TIMEOUT_MS,
  AuthProvider,
  bootstrapAuthSession,
  useAuth,
} from "@next/core/auth/session";
import * as authApi from "@next/core/api/auth";
import * as authStorage from "@next/core/auth/storage";

function AuthConsumer() {
  const { isAuthenticated, isLoading, restoreError, user } = useAuth();

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? ""}</span>
      <span data-testid="restore-error">{restoreError?.kind ?? ""}</span>
    </div>
  );
}

function makeAxiosError(status?: number): AxiosError {
  return new AxiosError(
    status ? `Request failed with status ${status}` : "Network Error",
    status ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_NETWORK,
    undefined,
    undefined,
    status
      ? {
          status,
          statusText: String(status),
          headers: {},
          config: { headers: {} },
          data: { detail: "Session rejected" },
        }
      : undefined,
  );
}

describe("bootstrapAuthSession", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns null session when there is no stored token", async () => {
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue(null);

    await expect(bootstrapAuthSession()).resolves.toEqual({ token: null, user: null, error: null });
  });

  it("loads the current user when a token exists", async () => {
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue({
      id: 1,
      email: "test@test.com",
      full_name: "Anita",
      is_active: true,
      created_at: "2026-04-28T00:00:00Z",
    });

    await expect(bootstrapAuthSession()).resolves.toEqual({
      token: "token-123",
      user: {
        id: 1,
        email: "test@test.com",
        full_name: "Anita",
        is_active: true,
        created_at: "2026-04-28T00:00:00Z",
      },
      error: null,
    });
  });

  it.each([401, 403])("clears invalid tokens when current user lookup returns %s", async (status) => {
    authStorage.setStoredToken("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(makeAxiosError(status));

    await expect(bootstrapAuthSession()).resolves.toEqual({ token: null, user: null, error: null });
    expect(authStorage.getStoredToken()).toBeNull();
  });

  it("preserves a potentially valid token when the backend is unreachable", async () => {
    authStorage.setStoredToken("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(makeAxiosError());

    await expect(bootstrapAuthSession()).resolves.toMatchObject({
      token: "token-123",
      user: null,
      error: { kind: "network", status: null },
    });
    expect(authStorage.getStoredToken()).toBe("token-123");
  });

  it.each([
    [500, "server"],
    [422, "unexpected"],
  ] as const)("preserves the token after HTTP %i and exposes a recoverable %s error", async (status, kind) => {
    authStorage.setStoredToken("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(makeAxiosError(status));

    await expect(bootstrapAuthSession()).resolves.toMatchObject({
      token: "token-123",
      user: null,
      error: { kind, status },
    });
    expect(authStorage.getStoredToken()).toBe("token-123");
  });

  it("resolves a request that never settles as a recoverable timeout", async () => {
    vi.useFakeTimers();
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockReturnValue(new Promise(() => undefined));

    const sessionPromise = bootstrapAuthSession();
    await vi.advanceTimersByTimeAsync(AUTH_RESTORE_TIMEOUT_MS);

    await expect(sessionPromise).resolves.toMatchObject({
      token: "token-123",
      user: null,
      error: { kind: "timeout" },
    });
    expect(authApi.getCurrentUser).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("bootstraps the authenticated session on page load", async () => {
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue({
      id: 1,
      email: "test@test.com",
      full_name: "Anita",
      is_active: true,
      created_at: "2026-04-28T00:00:00Z",
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    expect(screen.getByTestId("email")).toHaveTextContent("test@test.com");
  });

  it("always leaves loading after a restoration timeout", async () => {
    vi.useFakeTimers();
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockReturnValue(new Promise(() => undefined));

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    expect(screen.getByTestId("loading")).toHaveTextContent("true");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTH_RESTORE_TIMEOUT_MS);
    });

    expect(screen.getByTestId("loading")).toHaveTextContent("false");
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("restore-error")).toHaveTextContent("timeout");
    vi.useRealTimers();
  });
});
