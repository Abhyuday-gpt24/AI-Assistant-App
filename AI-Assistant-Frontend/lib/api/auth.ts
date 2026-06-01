import { apiFetch, parseError } from "./client";

export type AuthCredentials = {
  email: string;
  password: string;
};

export type SignupPayload = AuthCredentials & {
  name: string;
};

export type User = {
  id: string;
  name: string;
};

export type AuthResponse = {
  message: string;
  user: User;
};

export type LogoutResponse = {
  message: string;
};

export async function signup(payload: SignupPayload): Promise<AuthResponse> {
  const res = await apiFetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as AuthResponse;
}

export async function login(payload: AuthCredentials): Promise<AuthResponse> {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as AuthResponse;
}

export async function logout(): Promise<LogoutResponse> {
  const res = await apiFetch("/api/auth/logout", { method: "POST" });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as LogoutResponse;
}
