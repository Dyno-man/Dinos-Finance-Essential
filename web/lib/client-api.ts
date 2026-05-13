const browserApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function publicApiUrl(path: string) {
  return `${browserApiBase}${path}`;
}

export async function browserApi(path: string, init: RequestInit = {}) {
  const isFormData = init.body instanceof FormData;
  return fetch(`${browserApiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers ?? {}),
    },
  });
}

export async function jsonApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await browserApi(path, init);
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Request failed");
  }
  return response.json();
}

export async function uploadReceipt(file: File): Promise<{ receipt_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return jsonApi("/receipts/upload", { method: "POST", body: formData });
}
