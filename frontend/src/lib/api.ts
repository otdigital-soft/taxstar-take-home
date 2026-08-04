import { getToken, clearAuth } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

export type ApiErrorBody = {
  code: string;
  message: string;
  fields?: Record<string, string>;
};

export class ApiError extends Error {
  status: number;
  code: string;
  fields?: Record<string, string>;

  constructor(body: ApiErrorBody, status: number) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.fields = body.fields;
  }
}

function parseError(data: unknown, fallback: string, status: number): ApiError {
  if (
    data &&
    typeof data === "object" &&
    "error" in data &&
    data.error &&
    typeof data.error === "object" &&
    "message" in data.error
  ) {
    const err = data.error as ApiErrorBody;
    return new ApiError(
      {
        code: err.code || "error",
        message: err.message || fallback,
        fields: err.fields,
      },
      status,
    );
  }
  return new ApiError({ code: "error", message: fallback }, status);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearAuth();
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login")
      ) {
        window.location.href = "/login";
      }
    }
    throw parseError(data, res.statusText || "Request failed", res.status);
  }
  return data as T;
}

export type Entity = {
  id: string;
  name: string;
  trn_masked: string;
  created_at: string | null;
};

export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue";

export type Invoice = {
  id: string;
  entity_id: string;
  invoice_number: string;
  amount: string;
  currency: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  effective_status: InvoiceStatus;
  created_at: string | null;
};

export type AuthResponse = {
  token: string;
  user: { id: string; email: string; name: string };
};

export const api = {
  signup: (body: { email: string; password: string; name: string }) =>
    request<AuthResponse>(
      "/api/auth/signup",
      { method: "POST", body: JSON.stringify(body) },
      false,
    ),

  login: (body: { email: string; password: string }) =>
    request<AuthResponse>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify(body) },
      false,
    ),

  listEntities: () => request<Entity[]>("/api/entities"),

  createEntity: (body: { name: string; trn: string }) =>
    request<Entity>("/api/entities", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getEntity: (id: string) => request<Entity>(`/api/entities/${id}`),

  listInvoices: (params: { entity_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params.entity_id) q.set("entity_id", params.entity_id);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return request<Invoice[]>(`/api/invoices${qs ? `?${qs}` : ""}`);
  },

  createInvoice: (body: {
    entity_id: string;
    invoice_number: string;
    amount: string;
    currency: string;
    issue_date: string;
    due_date: string;
    status: string;
  }) =>
    request<Invoice>("/api/invoices", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateInvoiceStatus: (id: string, status: string) =>
    request<Invoice>(`/api/invoices/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
