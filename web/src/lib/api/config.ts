const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_CSRF_COOKIE = "lms_csrf";

export function getPublicApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL ?? LOCAL_API_BASE_URL;
  const parsed = new URL(configured);
  if (!(["http:", "https:"] as const).includes(parsed.protocol as "http:" | "https:")) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS.");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an origin without a path.");
  }
  if (parsed.hostname.endsWith("supabase.co") || parsed.hostname.endsWith("supabase.com")) {
    throw new Error("The dashboard must connect to FastAPI, not directly to Supabase.");
  }
  return parsed.origin;
}

export function getCsrfCookieName(): string {
  const name = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? DEFAULT_CSRF_COOKIE;
  if (!/^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/.test(name)) {
    throw new Error("NEXT_PUBLIC_CSRF_COOKIE_NAME must be a valid cookie token.");
  }
  return name;
}
