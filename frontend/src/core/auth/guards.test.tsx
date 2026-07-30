import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AuthGuard, GuestGuard } from "./guards";

const authSessionMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

vi.mock("./session", () => authSessionMock);

function renderProtectedRoute() {
  return render(
    <MemoryRouter initialEntries={["/datasets"]}>
      <Routes>
        <Route
          path="/datasets"
          element={
            <AuthGuard>
              <div>Protected content</div>
            </AuthGuard>
          }
        />
        <Route path="/login" element={<div>Login route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("auth guards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects an unauthenticated protected route to login", async () => {
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      restoreError: null,
    });

    renderProtectedRoute();

    expect(await screen.findByText("Login route")).toBeInTheDocument();
  });

  it("renders protected content for a restored session", () => {
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      restoreError: null,
    });

    renderProtectedRoute();

    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("shows a recoverable error instead of an indefinite loader", () => {
    const retrySession = vi.fn();
    const logout = vi.fn();
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      restoreError: {
        kind: "timeout",
        message: "The server took too long to validate the saved session.",
        status: null,
        requestId: null,
      },
      retrySession,
      logout,
    });

    renderProtectedRoute();

    expect(screen.getByText("Session validation unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    fireEvent.click(screen.getByRole("button", { name: "Back to sign in" }));
    expect(retrySession).toHaveBeenCalledTimes(1);
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("does not redirect-loop a guest route while restoration has failed", () => {
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      restoreError: {
        kind: "network",
        message: "The server is unreachable.",
        status: null,
        requestId: null,
      },
      retrySession: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <GuestGuard>
          <div>Login form</div>
        </GuestGuard>
      </MemoryRouter>,
    );

    expect(screen.getByText("Session validation unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Login form")).not.toBeInTheDocument();
  });
});
