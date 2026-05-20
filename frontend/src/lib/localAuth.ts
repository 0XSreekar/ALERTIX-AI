/**
 * Local auth client — calls FastAPI /api/auth/* instead of Supabase.
 * Drop-in replacement so Login/Signup pages work without a real Supabase project.
 */

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "alertix_token";
const USER_KEY = "alertix_user";

export interface LocalUser {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): LocalUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

function saveSession(token: string, user: LocalUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function signUp(email: string, password: string, fullName: string) {
  const res = await fetch(`${API}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Signup failed");
  saveSession(data.access_token, {
    user_id: data.user_id, email: data.email,
    full_name: data.full_name, role: data.role,
  });
  return data;
}

export async function signIn(email: string, password: string) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  saveSession(data.access_token, {
    user_id: data.user_id, email: data.email,
    full_name: data.full_name, role: data.role,
  });
  return data;
}

export function signOut() {
  clearSession();
}
