/**
 * Local auth client — talks to the FastAPI /api/auth/* endpoints.
 *
 * The HS256 JWT is set by the backend as an HttpOnly Secure cookie
 * (`alertix_token`) so JavaScript cannot read it; this contains the XSS blast
 * radius. We keep a copy of the *user metadata* (no token) in localStorage so
 * the UI can render role-aware nav without an extra round-trip on every page.
 *
 * Calls must use `credentials: 'include'` so the browser sends the cookie.
 */

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const USER_KEY = "alertix_user";

export interface LocalUser {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
}

export function getUser(): LocalUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

function saveUser(user: LocalUser) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(USER_KEY);
}

export async function signUp(email: string, password: string, fullName: string) {
  const res = await fetch(`${API}/api/auth/signup`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Signup failed");
  saveUser({
    user_id: data.user_id, email: data.email,
    full_name: data.full_name, role: data.role,
  });
  return data;
}

export async function signIn(email: string, password: string) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  saveUser({
    user_id: data.user_id, email: data.email,
    full_name: data.full_name, role: data.role,
  });
  return data;
}

export async function signOut() {
  try {
    await fetch(`${API}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Network error — local cleanup still happens below
  }
  clearSession();
}

/**
 * Verify the session with the backend. The JWT lives in an HttpOnly cookie so
 * we cannot inspect its `exp` from JS; instead we ask the server. Called by
 * ProtectedRoute on mount and after window regains focus. On failure, clears
 * cached user metadata and the api-fetch layer will redirect to /login.
 */
export async function verifySession(): Promise<LocalUser | null> {
  try {
    const res = await fetch(`${API}/api/auth/me`, {
      method: "GET",
      credentials: "include",
    });
    if (!res.ok) {
      clearSession();
      return null;
    }
    const data = await res.json();
    const user: LocalUser = {
      user_id: data.user_id,
      email: data.email ?? "",
      full_name: data.full_name ?? "",
      role: data.role,
    };
    saveUser(user);
    return user;
  } catch {
    return getUser(); // network blip — fall back to cached metadata
  }
}

/**
 * Exchange the HttpOnly cookie for a short-lived (60s) WebSocket ticket.
 * The ticket is scope='ws' so the backend rejects it on REST endpoints —
 * this stops a leaked WS query-param token from being replayed against the API.
 */
export async function getWsTicket(): Promise<string | null> {
  try {
    const res = await fetch(`${API}/api/auth/ws-ticket`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.token ?? null;
  } catch {
    return null;
  }
}
