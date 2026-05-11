import { beforeEach, describe, expect, it, vi } from "vitest";

import { nextApiClient } from "./client";
import { getCurrentUser, login, register } from "./auth";

vi.mock("./client", () => ({
  nextApiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("auth api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends register payload as JSON with full_name", async () => {
    vi.mocked(nextApiClient.post).mockResolvedValue({
      data: {
        id: 1,
        email: "test@test.com",
        full_name: "Anita",
        is_active: true,
        created_at: "2026-04-28T00:00:00Z",
      },
    });

    await register({
      email: "test@test.com",
      password: "12345678",
      full_name: "Anita",
    });

    expect(nextApiClient.post).toHaveBeenCalledWith("/auth/register", {
      email: "test@test.com",
      password: "12345678",
      full_name: "Anita",
    });
  });

  it("sends login payload as JSON with email and password", async () => {
    vi.mocked(nextApiClient.post).mockResolvedValue({
      data: {
        access_token: "token-123",
        token_type: "bearer",
      },
    });

    await login({
      email: "test@test.com",
      password: "12345678",
    });

    expect(nextApiClient.post).toHaveBeenCalledWith("/auth/login", {
      email: "test@test.com",
      password: "12345678",
    });
  });

  it("fetches current user from /users/me", async () => {
    vi.mocked(nextApiClient.get).mockResolvedValue({
      data: {
        id: 1,
        email: "test@test.com",
        full_name: "Anita",
        is_active: true,
        created_at: "2026-04-28T00:00:00Z",
      },
    });

    await getCurrentUser();

    expect(nextApiClient.get).toHaveBeenCalledWith("/users/me");
  });
});
