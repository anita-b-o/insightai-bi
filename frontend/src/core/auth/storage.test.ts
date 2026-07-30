import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_SESSION_INVALIDATED_EVENT,
  clearStoredToken,
  getStoredToken,
  invalidateStoredToken,
  setStoredToken,
} from "@next/core/auth/storage";

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

  it("invalidates only the token used by the rejected request", () => {
    const invalidated = vi.fn();
    globalThis.addEventListener(AUTH_SESSION_INVALIDATED_EVENT, invalidated);
    setStoredToken("new-token");

    expect(invalidateStoredToken("old-token")).toBe(false);
    expect(getStoredToken()).toBe("new-token");
    expect(invalidated).not.toHaveBeenCalled();

    expect(invalidateStoredToken("new-token")).toBe(true);
    expect(getStoredToken()).toBeNull();
    expect(invalidated).toHaveBeenCalledTimes(1);
    globalThis.removeEventListener(AUTH_SESSION_INVALIDATED_EVENT, invalidated);
  });
});
