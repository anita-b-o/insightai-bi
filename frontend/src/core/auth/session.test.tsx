import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, bootstrapAuthSession, useAuth } from "@next/core/auth/session";
import * as authApi from "@next/core/api/auth";
import * as authStorage from "@next/core/auth/storage";

function AuthConsumer() {
  const { isAuthenticated, isLoading, user } = useAuth();

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? ""}</span>
    </div>
  );
}

describe("bootstrapAuthSession", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null session when there is no stored token", async () => {
    vi.spyOn(authStorage, "getStoredToken").mockReturnValue(null);

    await expect(bootstrapAuthSession()).resolves.toEqual({ token: null, user: null });
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
    });
  });

  it("clears invalid tokens when current user lookup fails", async () => {
    const clearStoredToken = vi.spyOn(authStorage, "clearStoredToken").mockImplementation(() => undefined);

    vi.spyOn(authStorage, "getStoredToken").mockReturnValue("token-123");
    vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(new Error("Unauthorized"));

    await expect(bootstrapAuthSession()).resolves.toEqual({ token: null, user: null });
    expect(clearStoredToken).toHaveBeenCalledTimes(1);
  });
});

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
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
});
