const TOKEN_KEY = "insightai.bi.token";
export const AUTH_SESSION_INVALIDATED_EVENT = "insightai:auth-session-invalidated";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function invalidateStoredToken(expectedToken?: string): boolean {
  const currentToken = getStoredToken();
  if (!currentToken || (expectedToken !== undefined && currentToken !== expectedToken)) {
    return false;
  }

  clearStoredToken();
  globalThis.dispatchEvent(new CustomEvent(AUTH_SESSION_INVALIDATED_EVENT));
  return true;
}
