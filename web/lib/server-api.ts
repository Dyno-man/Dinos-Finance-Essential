import { cookies } from "next/headers";

export type AuthUser = {
  id: string;
  username: string;
  email: string | null;
  role: string;
  plan: string;
};

const serverApiBase = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getCurrentUser(): Promise<AuthUser | null> {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${serverApiBase}/auth/me`, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return response.json();
}
