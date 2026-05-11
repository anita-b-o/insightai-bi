import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { NextLoginPage } from "@next/pages/login-page";
import { NextRegisterPage } from "@next/pages/register-page";

const authSessionMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

vi.mock("@next/core/auth/session", () => authSessionMock);

describe("auth pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects to the intended route after login", async () => {
    const loginUser = vi.fn().mockResolvedValue(undefined);
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      loginUser,
    });

    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/login", state: { from: { pathname: "/datasets/upload" } } }]}
      >
        <Routes>
          <Route path="/login" element={<NextLoginPage />} />
          <Route path="/datasets/upload" element={<div>Upload page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: "test@test.com" } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: "12345678" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(loginUser).toHaveBeenCalledWith({
        email: "test@test.com",
        password: "12345678",
      });
    });

    await screen.findByText("Upload page");
  });

  it("redirects to the intended route after register", async () => {
    const registerUser = vi.fn().mockResolvedValue(undefined);
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      registerUser,
    });

    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/register", state: { from: { pathname: "/datasets/upload" } } }]}
      >
        <Routes>
          <Route path="/register" element={<NextRegisterPage />} />
          <Route path="/datasets/upload" element={<div>Upload page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: "Anita" } });
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: "test@test.com" } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: "12345678" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(registerUser).toHaveBeenCalledWith({
        full_name: "Anita",
        email: "test@test.com",
        password: "12345678",
      });
    });

    await screen.findByText("Upload page");
  });

  it("shows Try demo entry points on auth pages", () => {
    authSessionMock.useAuth.mockReturnValue({
      isAuthenticated: false,
      loginUser: vi.fn(),
      registerUser: vi.fn(),
    });

    const { rerender } = render(
      <MemoryRouter>
        <NextLoginPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Try demo" })).toHaveAttribute("href", "/demo");

    rerender(
      <MemoryRouter>
        <NextRegisterPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Try demo" })).toHaveAttribute("href", "/demo");
  });
});
