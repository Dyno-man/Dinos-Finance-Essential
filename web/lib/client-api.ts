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
    throw new Error(body.error?.message ?? body.detail?.message ?? body.detail ?? "Request failed");
  }
  return response.json();
}

export type UploadReceiptResponse = {
  receipt_id: string;
  status: string;
  duplicate: boolean;
  message?: string;
};

function uploadErrorMessage(status: number, responseText: string) {
  const body = responseText ? JSON.parse(responseText) : {};
  return body.error?.message ?? body.detail?.message ?? body.detail ?? `Upload failed with status ${status}`;
}

export async function uploadReceipt(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadReceiptResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${browserApiBase}/receipts/upload`);
    request.withCredentials = true;

    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    request.onload = () => {
      if (request.status === 401) {
        window.location.href = "/login";
        reject(new Error("Not authenticated"));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        try {
          reject(new Error(uploadErrorMessage(request.status, request.responseText)));
        } catch {
          reject(new Error("Upload failed. Try another receipt image."));
        }
        return;
      }
      try {
        resolve(JSON.parse(request.responseText) as UploadReceiptResponse);
      } catch {
        reject(new Error("Upload completed, but the server response was invalid."));
      }
    };
    request.onerror = () => reject(new Error("Upload failed. Check your connection and try again."));
    request.send(formData);
  });
}
