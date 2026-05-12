"use client";

import { useRouter } from "next/navigation";
import { browserApi } from "@/lib/client-api";

export function LogoutButton() {
  const router = useRouter();

  async function logout() {
    await browserApi("/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <button className="secondary" type="button" onClick={logout}>
      Log out
    </button>
  );
}
