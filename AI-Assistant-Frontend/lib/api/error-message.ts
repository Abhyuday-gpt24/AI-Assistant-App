import { ApiError } from "./client";

// Normalize anything thrown by an API call into a user-facing string. Prefers an
// ApiError's server message, then a plain Error's message, then the fallback.
export function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}
