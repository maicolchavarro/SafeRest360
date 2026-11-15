"use client";

import { useEffect, useState } from "react";
import { Ban, Clock, Pause, Pencil, Play, Plus, Trash2, UserX, Users, X } from "lucide-react";
import { rules as rulesApi } from "@/lib/api";
import type { Rule, RuleSchedule, RuleType, Severity, Zone } from "@/lib/types";
import { cn, severityColor } from "@/lib/utils";
import { formatDuration } from "@/lib/zone-state";

const TYPES: Record<RuleType, { label: string; description: string; icon: typeof Ban }> = {
  no_entry: {
    label: "Entrada prohibida",
    description: "Avisa cuando alguien permanece dentro de la zona.",
    icon: Ban,
  },
  zone_abandoned: {
    label: "Zona sin personal",
    description: "Avisa cuando la zona queda vacía más tiempo del permitido (caja, cocina, barra).",
    icon: UserX,
  },
  max_occupancy: {
    label: "Aforo máximo",
    description: "Avisa cuando hay más personas de las permitidas en la zona.",
    icon: Users,
  },
};

const SEVERITIES: { value: Severity; label: string }[] = [
  { value: "low", label: "Baja" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Crítica" },
];

const DAYS = ["L", "M", "X", "J", "V", "S", "D"];
const DAY_NAMES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];

interface Draft {
  id?: string;
  rule_type: RuleType;
  confirm_seconds: number;
  timeout_minutes: number;
  timeout_seconds: number;
  max_persons: number;
  severity: Severity;
  cooldown_minutes: number;
  scheduled: boolean;
  schedule: RuleSchedule;
}

const DEFAULT_SCHEDULE: RuleSchedule = { days: [0, 1, 2, 3, 4, 5, 6], start: "22:00", end: "06:00" };

function toDraft(rule?: Rule, zoneType?: Zone["zone_type"]): Draft {
  const timeout = rule?.parameters.timeout_seconds ?? 120;
  const fallbackType: RuleType = zoneType === "restricted" ? "no_entry" : "zone_abandoned";
  return {
    id: rule?.id,
    rule_type: rule?.rule_type ?? fallbackType,
    confirm_seconds: rule?.parameters.confirm_seconds ?? 2,
    timeout_minutes: Math.floor(timeout / 60),
    timeout_seconds: timeout % 60,
    max_persons: rule?.parameters.max_persons ?? 5,
    severity: rule?.severity ?? "medium",
    cooldown_minutes: Math.round((rule?.cooldown_seconds ?? 300) / 60),
    scheduled: !!rule?.schedule,
    schedule: rule?.schedule ?? DEFAULT_SCHEDULE,
  };
}

function toPayload(d: Draft): Partial<Rule> {
  const parameters: Rule["parameters"] =
    d.rule_type === "zone_abandoned"
      ? { timeout_seconds: d.timeout_minutes * 60 + d.timeout_seconds }
      : d.rule_type === "max_occupancy"
        ? { max_persons: d.max_persons, confirm_seconds: d.confirm_seconds }
        : { confirm_seconds: d.confirm_seconds };
  return {
    rule_type: d.rule_type,
    parameters,
    severity: d.severity,
    cooldown_seconds: Math.round(d.cooldown_minutes * 60),
    schedule: d.scheduled ? d.schedule : null,
  };
}

export function describeSchedule(s: RuleSchedule | null): string {
  if (!s) return "Siempre activa";
  const days = s.days.length === 7 ? "Todos los días" : s.days.map((d) => DAY_NAMES[d]).join(", ");
  const hours = s.start === s.end ? "todo el día" : `${s.start}–${s.end}${s.end <= s.start ? " (+1 día)" : ""}`;
  return `${days}, ${hours}`;
}

function describeRule(r: Rule): string {
  const p = r.parameters;
  switch (r.rule_type) {
    case "zone_abandoned":
      return `Alerta si queda sin personal ${formatDuration(p.timeout_seconds ?? 120)}`;
    case "max_occupancy":
      return `Alerta con más de ${p.max_persons} personas durante ${p.confirm_seconds ?? 0} s`;
    default:
      return `Alerta si alguien permanece ${p.confirm_seconds ?? 0} s dentro`;
  }
}

function apiError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msg = (detail[0] as { msg?: string })?.msg;
    if (msg) return msg.replace(/^Value error, /, "");
  }
  return "No se pudo guardar la regla";
}

function NumberField({ label, value, onChange, min, max, suffix, help }: {
  label: string; value: number; onChange: (v: number) => void; min: number; max: number; suffix?: string; help?: string;
}) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-gray-700 mb-1">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="number" min={min} max={max} value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-28 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
        {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
      </div>
      {help && <span className="block text-xs text-gray-400 mt-1">{help}</span>}
    </label>
  );
}

function RuleForm({ initial, onCancel, onSaved, zoneId }: {
  initial: Draft; onCancel: () => void; onSaved: () => void; zoneId: string;
}) {
  const [d, setD] = useState<Draft>(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }));
  const toggleDay = (day: number) =>
    set({ schedule: { ...d.schedule, days: d.schedule.days.includes(day) ? d.schedule.days.filter((x) => x !== day) : [...d.schedule.days, day].sort() } });

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      if (d.id) await rulesApi.update(d.id, toPayload(d));
      else await rulesApi.create(zoneId, toPayload(d));
      onSaved();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      {error && <div className="p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>}

      <div>
        <span className="block text-sm font-medium text-gray-700 mb-2">Tipo de regla</span>
        <div className="grid gap-2 sm:grid-cols-3">
          {(Object.keys(TYPES) as RuleType[]).map((t) => {
            const meta = TYPES[t];
            const Icon = meta.icon;
            return (
              <button
                key={t} type="button" onClick={() => set({ rule_type: t })}
                className={cn(
                  "text-left p-3 rounded-lg border transition-colors",
                  d.rule_type === t ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500" : "hover:bg-gray-50"
                )}
              >
                <Icon className="h-4 w-4 mb-1 text-gray-700" />
                <div className="text-sm font-medium text-gray-900">{meta.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{meta.description}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {d.rule_type === "zone_abandoned" && (
          <div>
            <span className="block text-sm font-medium text-gray-700 mb-1">Tiempo máximo sin personal</span>
            <div className="flex items-center gap-2">
              <input type="number" min={0} max={1440} value={d.timeout_minutes}
                onChange={(e) => set({ timeout_minutes: Number(e.target.value) })}
                className="w-20 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
              <span className="text-sm text-gray-500">min</span>
              <input type="number" min={0} max={59} value={d.timeout_seconds}
                onChange={(e) => set({ timeout_seconds: Number(e.target.value) })}
                className="w-20 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
              <span className="text-sm text-gray-500">s</span>
            </div>
            <span className="block text-xs text-gray-400 mt-1">Mínimo 10 s. La cuenta regresiva se ve sobre la zona en vivo.</span>
          </div>
        )}
        {d.rule_type === "max_occupancy" && (
          <NumberField label="Máximo de personas" value={d.max_persons} min={1} max={100}
            onChange={(v) => set({ max_persons: v })} suffix="personas" />
        )}
        {d.rule_type !== "zone_abandoned" && (
          <NumberField label="Confirmar durante" value={d.confirm_seconds} min={0} max={600} suffix="segundos"
            onChange={(v) => set({ confirm_seconds: v })}
            help="La condición debe mantenerse este tiempo; evita alertas por detecciones de un instante." />
        )}
        <NumberField label="Esperar entre avisos" value={d.cooldown_minutes} min={0} max={1440} suffix="minutos"
          onChange={(v) => set({ cooldown_minutes: v })}
          help="Mientras la situación continúe, no se repite la alerta antes de este tiempo." />
      </div>

      <div>
        <span className="block text-sm font-medium text-gray-700 mb-2">Gravedad</span>
        <div className="flex flex-wrap gap-2">
          {SEVERITIES.map((s) => (
            <button key={s.value} type="button" onClick={() => set({ severity: s.value })}
              className={cn(
                "px-3 py-1.5 text-sm rounded-lg border",
                d.severity === s.value ? cn(severityColor(s.value), "border-current font-medium") : "text-gray-600 hover:bg-gray-50"
              )}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <span className="block text-sm font-medium text-gray-700 mb-2">Horario</span>
        <div className="flex gap-4 text-sm mb-3">
          <label className="flex items-center gap-2">
            <input type="radio" checked={!d.scheduled} onChange={() => set({ scheduled: false })} /> Siempre activa
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={d.scheduled} onChange={() => set({ scheduled: true })} /> Solo en un horario
          </label>
        </div>
        {d.scheduled && (
          <div className="p-3 rounded-lg bg-gray-50 space-y-3">
            <div className="flex gap-1.5">
              {DAYS.map((label, day) => (
                <button key={day} type="button" onClick={() => toggleDay(day)}
                  className={cn(
                    "w-9 h-9 rounded-full text-sm font-medium",
                    d.schedule.days.includes(day) ? "bg-blue-600 text-white" : "bg-white border text-gray-500"
                  )}>
                  {label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-gray-400" />
              <span>Desde</span>
              <input type="time" value={d.schedule.start}
                onChange={(e) => set({ schedule: { ...d.schedule, start: e.target.value } })}
                className="px-2 py-1.5 border rounded-lg" />
              <span>hasta</span>
              <input type="time" value={d.schedule.end}
                onChange={(e) => set({ schedule: { ...d.schedule, end: e.target.value } })}
                className="px-2 py-1.5 border rounded-lg" />
            </div>
            <p className="text-xs text-gray-500">
              {describeSchedule(d.schedule)} · hora del restaurante. Si la hora final es menor, la regla sigue hasta el día siguiente.
            </p>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2 pt-2 border-t">
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
        <button onClick={save} disabled={saving}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {saving ? "Guardando…" : d.id ? "Guardar cambios" : "Crear regla"}
        </button>
      </div>
    </div>
  );
}

export function RuleEditor({ zone, onClose }: { zone: Zone; onClose: () => void }) {
  const [list, setList] = useState<Rule[]>([]);
  const [editing, setEditing] = useState<Draft | null>(null);
  const [error, setError] = useState("");

  const load = () => rulesApi.list(zone.id).then((r) => setList(r.data)).catch(() => setError("No se pudieron cargar las reglas"));
  useEffect(() => { load(); }, [zone.id]);

  const toggle = async (r: Rule) => {
    await rulesApi.update(r.id, { is_active: !r.is_active });
    load();
  };

  const remove = async (r: Rule) => {
    setError("");
    try {
      await rulesApi.delete(r.id);
      load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between p-5 border-b sticky top-0 bg-white">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Reglas · {zone.name}</h2>
            <p className="text-sm text-gray-500">Los cambios se aplican a la cámara en unos segundos.</p>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-700"><X className="h-5 w-5" /></button>
        </div>

        <div className="p-5">
          {error && <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>}

          {editing ? (
            <RuleForm
              initial={editing}
              zoneId={zone.id}
              onCancel={() => setEditing(null)}
              onSaved={() => { setEditing(null); load(); }}
            />
          ) : (
            <>
              <div className="space-y-3">
                {list.length === 0 && <p className="text-sm text-gray-500">Esta zona no tiene reglas; no generará alertas.</p>}
                {list.map((r) => {
                  const meta = TYPES[r.rule_type] ?? TYPES.no_entry;
                  const Icon = meta.icon;
                  return (
                    <div key={r.id} className={cn("p-4 rounded-lg border", !r.is_active && "bg-gray-50 opacity-70")}>
                      <div className="flex items-start gap-3">
                        <Icon className="h-5 w-5 text-gray-600 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-gray-900">{meta.label}</span>
                            <span className={cn("px-2 py-0.5 text-xs rounded-full", severityColor(r.severity))}>
                              {SEVERITIES.find((s) => s.value === r.severity)?.label}
                            </span>
                            {!r.is_active && <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">Pausada</span>}
                          </div>
                          <p className="text-sm text-gray-700 mt-1">{describeRule(r)}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {describeSchedule(r.schedule)} · repite cada {formatDuration(r.cooldown_seconds)}
                          </p>
                        </div>
                        <div className="flex gap-1">
                          <button onClick={() => toggle(r)} title={r.is_active ? "Pausar" : "Reanudar"}
                            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
                            {r.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                          </button>
                          <button onClick={() => setEditing(toDraft(r))} title="Editar"
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button onClick={() => remove(r)} title="Eliminar"
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <button onClick={() => setEditing(toDraft(undefined, zone.zone_type))}
                className="mt-4 flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Plus className="h-4 w-4" /> Agregar regla
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
