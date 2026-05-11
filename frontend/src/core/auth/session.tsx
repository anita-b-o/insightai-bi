import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  getCurrentUser,
  login,
  register,
} from "@next/core/api/auth";
import { reportClientError } from "@next/app/client-error-reporting";
import type { LoginPayload, RegisterPayload, SessionUser } from "@next/core/types/auth";
import { clearStoredToken, getStoredToken, setStoredToken } from "./storage";

interface SessionContextValue {
  user: SessionUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginUser: (payload: LoginPayload) => Promise<void>;
  registerUser: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export async function bootstrapAuthSession(): Promise<{ token: string | null; user: SessionUser | null }> {
  const currentToken = getStoredToken();
  if (!currentToken) {
    return { token: null, user: null };
  }

  try {
    const currentUser = await getCurrentUser();
    return { token: currentToken, user: currentUser };
  } catch {
    void reportClientError({
      category: "auth_bootstrap_failed",
      message: "Stored session could not be restored",
    });
    clearStoredToken();
    return { token: null, user: null };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<SessionUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      const session = await bootstrapAuthSession();
      setToken(session.token);
      setUser(session.user);
      setIsLoading(false);
    }

    void bootstrap();
  }, []);

  async function loginUser(payload: LoginPayload) {
    const response = await login(payload);
    setStoredToken(response.access_token);
    setToken(response.access_token);
    const currentUser = await getCurrentUser();
    setUser(currentUser);
  }

  async function registerUser(payload: RegisterPayload) {
    await register(payload);
    await loginUser({ email: payload.email, password: payload.password });
  }

  function logout() {
    clearStoredToken();
    setToken(null);
    setUser(null);
  }

  return (
    <SessionContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(token && user),
        isLoading,
        loginUser,
        registerUser,
        logout,
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
