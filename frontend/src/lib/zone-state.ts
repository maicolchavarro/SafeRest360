import type { RuleLiveState, RuleLiveStatus } from "./types";

export type ZoneTone = "idle" | "ok" | "warn" | "alert";

export interface ZoneBadge {
  title: string;
  detail?: string;
  tone: ZoneTone;
}

export const TONE_COLORS: Record<ZoneTone, string> = {
  idle: "#6b7280",
  ok: "#16a34a",
  warn: "#f59e0b",
  alert: "#dc2626",
};

const PRIORITY: Record<RuleLiveStatus, number> = {
  intrusion: 3, unattended: 3, over_capacity: 3,
  confirming: 2, abandoned: 2,
  attended: 1, clear: 1,
  inactive: 0,
};

export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}:${String(s % 60).padStart(2, "0")}` : `${s} s`;
}

function plural(n: number) {
  return `${n} ${n === 1 ? "persona" : "personas"}`;
}

/** elapsed = seconds since the state was fetched, so countdowns keep ticking between polls */
export function badgeFor(state: RuleLiveState, elapsed: number): ZoneBadge {
  const toAlert = state.seconds_to_alert != null ? state.seconds_to_alert - elapsed : null;
  const repeat = state.next_alert_in != null ? state.next_alert_in - elapsed : null;
  const repeatText = repeat != null && repeat > 0 ? ` · repite en ${formatDuration(repeat)}` : "";

  switch (state.status) {
    case "inactive":
      return { title: "Fuera de horario", tone: "idle" };
    case "attended":
      return { title: "Atendida", detail: plural(state.persons), tone: "ok" };
    case "abandoned":
      return { title: "Abandonada", detail: `Aviso en ${formatDuration(toAlert ?? 0)}`, tone: "warn" };
    case "unattended":
      return { title: "Sin atender", detail: `Alerta enviada${repeatText}`, tone: "alert" };
    case "confirming":
      return {
        title: state.rule_type === "max_occupancy" ? "Aforo superado" : "Persona detectada",
        detail: `Confirmando ${formatDuration(toAlert ?? 0)}`,
        tone: "warn",
      };
    case "intrusion":
      return { title: "Intrusión", detail: `Alerta enviada${repeatText}`, tone: "alert" };
    case "over_capacity":
      return { title: `Aforo excedido · ${plural(state.persons)}`, detail: `Alerta enviada${repeatText}`, tone: "alert" };
    default:
      return {
        title: state.rule_type === "max_occupancy" ? plural(state.persons) : "Libre",
        tone: "idle",
      };
  }
}

/** One badge per zone: the most urgent of its rules */
export function zoneBadges(states: RuleLiveState[], elapsed: number): Record<string, ZoneBadge> {
  const best: Record<string, RuleLiveState> = {};
  for (const s of states) {
    const current = best[s.zone_id];
    if (!current || PRIORITY[s.status] > PRIORITY[current.status]) best[s.zone_id] = s;
  }
  return Object.fromEntries(Object.entries(best).map(([zoneId, s]) => [zoneId, badgeFor(s, elapsed)]));
}
