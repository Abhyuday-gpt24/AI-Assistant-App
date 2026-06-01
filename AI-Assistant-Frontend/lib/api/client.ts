export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ValidationErrorItem = {
  loc: (string | number)[];
  msg: string;
  type: string;
};

export class ApiError extends Error {
  status: number;
  details?: ValidationErrorItem[];

  constructor(message: string, status: number, details?: ValidationErrorItem[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export async function parseError(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`;
  let details: ValidationErrorItem[] | undefined;
  try {
    const body = (await res.json()) as { detail?: ValidationErrorItem[] | string };
    if (Array.isArray(body.detail)) {
      details = body.detail;
      message = body.detail[0]?.msg ?? message;
    } else if (typeof body.detail === "string") {
      message = body.detail;
    }
  } catch {
    // body wasn't JSON; keep status text
  }
  return new ApiError(message, res.status, details);
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

// Wrapped fetch: forces cookie credentials and bounces to /login on 401
// (unless we're already on /login or /signup, where a 401 is a bad-password
// error that the form needs to display itself).
export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const res = await fetch(apiUrl(path), { ...init, credentials: "include" });
  if (res.status === 401 && typeof window !== "undefined") {
    const current = window.location.pathname;
    if (current !== "/login" && current !== "/signup") {
      window.location.assign("/login");
    }
  }
  return res;
}
