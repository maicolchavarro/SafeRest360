import axios from "axios";
import type {
  Alert,
  Camera,
  CameraLiveStatus,
  DashboardSummary,
  Rule,
  TokenResponse,
  User,
  Zone,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const auth = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),
  refresh: (refresh_token: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token }),
  me: () => api.get<User>("/auth/me"),
};

export const cameras = {
  list: () => api.get<Camera[]>("/cameras"),
  get: (id: string) => api.get<Camera>(`/cameras/${id}`),
  create: (data: Partial<Camera>) => api.post<Camera>("/cameras", data),
  update: (id: string, data: Partial<Camera>) => api.patch<Camera>(`/cameras/${id}`, data),
  delete: (id: string) => api.delete(`/cameras/${id}`),
  liveFrame: (id: string) => api.get<Blob>(`/cameras/${id}/live.jpg`, { responseType: "blob" }),
  liveStatus: (id: string) => api.get<CameraLiveStatus>(`/cameras/${id}/live/status`),
};

export const zones = {
  list: (cameraId: string) => api.get<Zone[]>(`/cameras/${cameraId}/zones`),
  create: (cameraId: string, data: Partial<Zone>) =>
    api.post<Zone>(`/cameras/${cameraId}/zones`, data),
  update: (id: string, data: Partial<Zone>) => api.patch<Zone>(`/zones/${id}`, data),
  delete: (id: string) => api.delete(`/zones/${id}`),
};

export const rules = {
  list: (zoneId: string) => api.get<Rule[]>(`/zones/${zoneId}/rules`),
  create: (zoneId: string, data: Partial<Rule>) =>
    api.post<Rule>(`/zones/${zoneId}/rules`, data),
  update: (id: string, data: Partial<Rule>) => api.patch<Rule>(`/rules/${id}`, data),
  delete: (id: string) => api.delete(`/rules/${id}`),
};

export const alerts = {
  list: (params?: Record<string, string>) =>
    api.get<Alert[]>("/alerts", { params }),
  get: (id: string) => api.get<Alert>(`/alerts/${id}`),
  update: (id: string, data: { status: string }) =>
    api.patch<Alert>(`/alerts/${id}`, data),
  delete: (id: string) => api.delete(`/alerts/${id}`),
  cleanup: (older_than_days?: number) =>
    api.post("/alerts/cleanup", null, { params: older_than_days ? { older_than_days } : undefined }),
  snapshot: (id: string) => api.get<Blob>(`/alerts/${id}/snapshot`, { responseType: "blob" }),
};

export const dashboard = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
};

export const inference = {
  detect: (file: File, confidence?: number) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/inference/detect", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      params: confidence ? { confidence } : undefined,
    });
  },
  models: () => api.get("/inference/models"),
};

export default api;

export interface NotificationConfig {
  channel: "telegram" | "whatsapp" | "disabled";
  test_mode: boolean;
  credentials_configured: boolean;
  recipient_configured: boolean;
  retention_days: number;
}

export const notifications = {
  config: () => api.get<NotificationConfig>("/notifications/config"),
};
