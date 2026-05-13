import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type {
  AnalyticsSummary,
  AuthUser,
  BillingSummary,
  Category,
  Integration,
  ReceiptDetail,
  ReceiptListResponse,
} from "./types";

const serverApiBase = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function serverApi<T>(path: string): Promise<T> {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${serverApiBase}${path}`, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (response.status === 401) {
    redirect("/login");
  }
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return response.json();
}

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

export async function requireUser(): Promise<AuthUser> {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  return user;
}

export async function getReceipts(query = "") {
  return serverApi<ReceiptListResponse>(`/receipts${query}`);
}

export async function getReceiptDetail(id: string) {
  return serverApi<ReceiptDetail>(`/receipts/${id}`);
}

export async function getCategories() {
  return serverApi<{ categories: Category[] }>("/categories");
}

export async function getAnalytics(query = "") {
  return serverApi<AnalyticsSummary>(`/analytics/summary${query}`);
}

export async function getIntegrations() {
  return serverApi<{ integrations: Integration[] }>("/integrations");
}

export async function getBillingSummary() {
  return serverApi<BillingSummary>("/billing/summary");
}
