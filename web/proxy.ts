import { NextRequest, NextResponse } from "next/server";

const protectedRoutes = ["/dashboard", "/upload", "/receipts", "/analytics", "/integrations", "/billing", "/settings"];
const authRoutes = ["/login", "/register"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const apiBase = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${apiBase}/auth/me`, {
    headers: { cookie: request.headers.get("cookie") ?? "" },
    cache: "no-store",
  }).catch(() => null);
  const authenticated = response?.ok ?? false;

  if (protectedRoutes.some((route) => pathname.startsWith(route)) && !authenticated) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (authRoutes.includes(pathname) && authenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/upload/:path*",
    "/receipts/:path*",
    "/analytics/:path*",
    "/integrations/:path*",
    "/billing/:path*",
    "/settings/:path*",
    "/login",
    "/register",
  ],
};
