"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { browserApi } from "@/lib/client-api";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");

    if (mode === "register" && password !== String(form.get("confirmPassword") ?? "")) {
      setLoading(false);
      setError("Passwords do not match.");
      return;
    }

    const payload =
      mode === "register"
        ? {
            username: String(form.get("username") ?? ""),
            email: String(form.get("email") ?? "") || null,
            password,
          }
        : {
            username: String(form.get("username") ?? ""),
            password,
          };

    try {
      const response = await browserApi(`/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        setError(mode === "login" ? "Invalid username or password." : "Unable to create account.");
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch {
      setError("Could not reach the API. Make sure the backend is running on http://localhost:8000.");
    } finally {
      setLoading(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <div className="page">
      <section className="panel">
        <h1>{isRegister ? "Create account" : "Sign in"}</h1>
        <p>{isRegister ? "Start tracking receipt spending." : "Continue to your receipt dashboard."}</p>
        <form onSubmit={onSubmit}>
          <label>
            {isRegister ? "Username" : "Username or email"}
            <input name="username" autoComplete="username" required minLength={isRegister ? 3 : undefined} />
          </label>
          {isRegister ? (
            <label>
              Email
              <input name="email" type="email" autoComplete="email" />
            </label>
          ) : null}
          <label>
            Password
            <input name="password" type="password" autoComplete={isRegister ? "new-password" : "current-password"} required minLength={12} />
          </label>
          {isRegister ? (
            <label>
              Confirm password
              <input name="confirmPassword" type="password" autoComplete="new-password" required minLength={12} />
            </label>
          ) : null}
          <div className="error">{error}</div>
          <button type="submit" disabled={loading}>
            {loading ? "Working..." : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>
        <p>
          {isRegister ? "Already have an account? " : "Need an account? "}
          <Link href={isRegister ? "/login" : "/register"}>{isRegister ? "Sign in" : "Create one"}</Link>
        </p>
      </section>
    </div>
  );
}
