import { beforeEach, describe, expect, it } from "vitest";

import { clearStoredToken, getStoredToken, setStoredToken } from "@next/core/auth/storage";

describe("auth storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and reads the access token", () => {
    setStoredToken("token-123");

    expect(getStoredToken()).toBe("token-123");
  });

  it("clears the stored access token", () => {
    setStoredToken("token-123");

    clearStoredToken();

    expect(getStoredToken()).toBeNull();
  });
});
