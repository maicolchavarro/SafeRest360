export interface User {
  id: string;
  restaurant_id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "operator";
  phone_whatsapp: string | null;
  is_active: boolean;
}

export interface Camera {
  id: string;
  restaurant_id: string;
  name: string;
  location_description: string | null;
  stream_type: string;
  resolution_w: number | null;
  resolution_h: number | null;
  fps: number;
  status: "online" | "offline" | "error";
  last_heartbeat: string | null;
  is_active: boolean;
  has_stream_url: boolean;
  created_at: string;
}

export interface CameraLiveStatus {
  streaming: boolean;
  status: "online" | "offline" | "error";
  persons_in_view: number;
  analysis_fps: number;
  last_frame_at: string | null;
  error: string | null;
  rules: RuleLiveState[];
}

export interface PolygonPoint {
  x: number;
  y: number;
}

export interface Zone {
  id: string;
  camera_id: string;
  name: string;
  zone_type: "restricted" | "monitored" | "required_presence";
  polygon_points: PolygonPoint[];
  color: string;
  is_active: boolean;
}

export type RuleType = "no_entry" | "zone_abandoned" | "max_occupancy";
export type Severity = "low" | "medium" | "high" | "critical";

export interface RuleSchedule {
  days: number[]; // 0 = lunes
  start: string; // "HH:MM"
  end: string;
}

export interface Rule {
  id: string;
  zone_id: string;
  rule_type: RuleType;
  parameters: { confirm_seconds?: number; timeout_seconds?: number; max_persons?: number };
  schedule: RuleSchedule | null;
  severity: Severity;
  cooldown_seconds: number;
  is_active: boolean;
}

export type RuleLiveStatus =
  | "inactive" | "clear" | "confirming" | "intrusion" | "over_capacity"
  | "attended" | "abandoned" | "unattended";

export interface RuleLiveState {
  rule_id: string;
  zone_id: string;
  rule_type: RuleType;
  status: RuleLiveStatus;
  persons: number;
  seconds_to_alert: number | null;
  next_alert_in: number | null;
  condition_seconds: number | null;
}

export interface Alert {
  id: string;
  rule_id: string;
  camera_id: string;
  zone_id: string;
  restaurant_id: string;
  alert_type: string;
  severity: string;
  status: "new" | "acknowledged" | "resolved" | "false_alarm";
  description: string | null;
  has_snapshot: boolean;
  detection_data: Record<string, unknown> | null;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface DashboardSummary {
  total_cameras: number;
  cameras_online: number;
  cameras_offline: number;
  alerts_today: number;
  alerts_pending: number;
  zones_configured: number;
}

export interface Detection {
  bbox: number[];
  confidence: number;
  class_id: number;
  track_id: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
