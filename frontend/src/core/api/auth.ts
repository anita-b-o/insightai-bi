import type { AuthResponse, LoginPayload, RegisterPayload, SessionUser } from "@next/core/types/auth";

import { nextApiClient } from "./client";

export async function register(payload: RegisterPayload): Promise<SessionUser> {
  const { data } = await nextApiClient.post<SessionUser>("/auth/register", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await nextApiClient.post<AuthResponse>("/auth/login", payload);
  return data;
}

export async function getCurrentUser(): Promise<SessionUser> {
  const { data } = await nextApiClient.get<SessionUser>("/users/me");
  return data;
}
