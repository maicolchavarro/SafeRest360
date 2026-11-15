"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Plus, Trash2, ArrowLeft, Shield, Eye, UserCheck, Radio, Users, SlidersHorizontal } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { ZoneCanvas } from "@/components/zones/zone-canvas";
import { RuleEditor } from "@/components/rules/rule-editor";
import { cameras as camerasApi, zones as zonesApi } from "@/lib/api";
import type { Camera, CameraLiveStatus, Zone, PolygonPoint } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TONE_COLORS, zoneBadges } from "@/lib/zone-state";
import { useAuth } from "@/context/auth-context";

const CANVAS_WIDTH = 768;

function useLiveCamera(cameraId: string) {
  const [frame, setFrame] = useState<ImageBitmap | null>(null);
  const [status, setStatus] = useState<CameraLiveStatus | null>(null);
  const [fetchedAt, setFetchedAt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let delay = 300;
      try {
        const res = await camerasApi.liveFrame(cameraId);
        const bitmap = await createImageBitmap(res.data);
        if (cancelled) { bitmap.close(); return; }
        setFrame((prev) => { prev?.close(); return bitmap; });
      } catch {
        delay = 2000;
      }
      if (!cancelled) timer = setTimeout(poll, delay);
    };
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [cameraId]);

  useEffect(() => {
    let cancelled = false;
    const load = () => camerasApi.liveStatus(cameraId).then((r) => {
      if (!cancelled) { setStatus(r.data); setFetchedAt(Date.now()); }
    }).catch(() => {});
    load();
    const id = setInterval(load, 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [cameraId]);

  // re-render 4x/s so countdowns tick smoothly between status polls
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const badges = useMemo(
    () => (status?.status === "online" ? zoneBadges(status.rules, Math.max(0, (now - fetchedAt) / 1000)) : {}),
    [status, now, fetchedAt]
  );

  return { frame, status, badges };
}

const zoneTypeLabels: Record<string, { label: string; icon: typeof Shield }> = {
  restricted: { label: "Restringida", icon: Shield },
  monitored: { label: "Monitoreada", icon: Eye },
  required_presence: { label: "Presencia requerida", icon: UserCheck },
};

export default function CameraDetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>}>
      <CameraDetailInner />
    </Suspense>
  );
}

function CameraDetailInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [camera, setCamera] = useState<Camera | null>(null);
  const [zoneList, setZoneList] = useState<Zone[]>([]);
  const [activeZone, setActiveZone] = useState<string | undefined>();
  const [drawing, setDrawing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<{ name: string; zone_type: Zone["zone_type"]; color: string }>({ name: "", zone_type: "restricted", color: "#ef4444" });
  const [pendingPoints, setPendingPoints] = useState<PolygonPoint[]>([]);
  const { frame, status, badges } = useLiveCamera(id);
  const [rulesZone, setRulesZone] = useState<Zone | null>(null);
  const canvasHeight = frame ? Math.round((CANVAS_WIDTH * frame.height) / frame.width) : Math.round(CANVAS_WIDTH * 9 / 16);
  const online = status?.status === "online";

  const load = async () => {
    const [cam, z] = await Promise.all([camerasApi.get(id), zonesApi.list(id)]);
    setCamera(cam.data);
    setZoneList(z.data);
  };

  useEffect(() => { load(); }, [id]);

  const handleDrawComplete = (points: PolygonPoint[]) => {
    setPendingPoints(points);
    setDrawing(false);
    setShowForm(true);
  };

  const handleSaveZone = async () => {
    if (!form.name.trim()) return;
    await zonesApi.create(id, { ...form, polygon_points: pendingPoints });
    setShowForm(false);
    setPendingPoints([]);
    setForm({ name: "", zone_type: "restricted", color: "#ef4444" });
    load();
  };

  const handleDeleteZone = async (zoneId: string) => {
    await zonesApi.delete(zoneId);
    load();
  };

  const zoneColors: Record<string, string> = {
    restricted: "#ef4444",
    monitored: "#f59e0b",
    required_presence: "#22c55e",
  };

  return (
    <AppShell>
      <Topbar title={camera?.name || "Cámara"} />
      <div className="p-4 md:p-6">
        <button
          onClick={() => router.push("/cameras")}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Volver a cámaras
        </button>

        {/* Zone list above canvas on mobile */}
        <div className="mb-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Zonas ({zoneList.length})</h2>
              {user?.role === "admin" && (
                <button
                  onClick={() => setDrawing(!drawing)}
                  className={cn(
                    "flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg",
                    drawing ? "bg-red-100 text-red-700" : "bg-blue-600 text-white hover:bg-blue-700"
                  )}
                >
                  {drawing ? "Cancelar" : <><Plus className="h-4 w-4" /> Nueva zona</>}
                </button>
              )}
            </div>
            {zoneList.length === 0 ? (
              <p className="text-sm text-gray-500">Dibuja polígonos sobre la vista de cámara para definir zonas de vigilancia.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {zoneList.map((z) => {
                  const meta = zoneTypeLabels[z.zone_type] || zoneTypeLabels.restricted;
                  const ZIcon = meta.icon;
                  const badge = badges[z.id];
                  return (
                    <div
                      key={z.id}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors text-sm",
                        activeZone === z.id ? "border-blue-500 bg-blue-50" : "hover:bg-gray-50"
                      )}
                      onClick={() => setActiveZone(activeZone === z.id ? undefined : z.id)}
                    >
                      <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: z.color }} />
                      <ZIcon className="h-3.5 w-3.5 text-gray-400" />
                      <span className="font-medium text-gray-800">{z.name}</span>
                      <span className="text-xs text-gray-400">{meta.label}</span>
                      {badge && (
                        <span
                          className="px-2 py-0.5 text-xs font-medium rounded-full text-white tabular-nums"
                          style={{ backgroundColor: TONE_COLORS[badge.tone] }}
                        >
                          {badge.title}{badge.detail ? ` · ${badge.detail}` : ""}
                        </span>
                      )}
                      {user?.role === "admin" && (
                        <>
                          <button
                            onClick={(e) => { e.stopPropagation(); setRulesZone(z); }}
                            className="flex items-center gap-1 px-2 py-0.5 text-xs text-blue-700 hover:bg-blue-100 rounded ml-1"
                            title="Configurar reglas"
                          >
                            <SlidersHorizontal className="h-3 w-3" /> Reglas
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteZone(z.id); }}
                            className="p-0.5 text-gray-300 hover:text-red-600"
                            title="Eliminar zona"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Live view + zones */}
        <div className="bg-white rounded-xl border p-4">
          <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
            <span className={cn(
              "flex items-center gap-1.5 px-2 py-0.5 rounded-full font-medium",
              online ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
            )}>
              <Radio className="h-3.5 w-3.5" />
              {online ? "En vivo" : status?.streaming ? "Conectando…" : "Sin stream"}
            </span>
            {online && (
              <>
                <span className="flex items-center gap-1 text-gray-600">
                  <Users className="h-4 w-4" /> {status?.persons_in_view ?? 0} personas en vista
                </span>
                <span className="text-gray-400">{status?.analysis_fps ?? 0} cuadros analizados/s</span>
              </>
            )}
            {status?.error && <span className="text-amber-600">{status.error}</span>}
          </div>
          {drawing && (
            <p className="text-sm text-blue-600 mb-2">
              Clic para agregar vértices · Doble clic para cerrar · Clic derecho para deshacer
            </p>
          )}
          <ZoneCanvas
            width={CANVAS_WIDTH}
            height={canvasHeight}
            zones={zoneList}
            activeZoneId={activeZone}
            drawing={drawing}
            onDrawComplete={handleDrawComplete}
            background={frame}
            badges={badges}
            placeholder={camera?.has_stream_url ? "Conectando con la cámara…" : "Configura la URL RTSP de la cámara para ver la imagen"}
          />
          <p className="text-xs text-gray-400 mt-2">
            Las imágenes en vivo no se almacenan; solo se guarda una foto cuando se genera una alerta.
          </p>
        </div>

        {rulesZone && <RuleEditor zone={rulesZone} onClose={() => setRulesZone(null)} />}

        {/* Zone save form */}
        {showForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-4">
              <h2 className="text-lg font-semibold">Nueva zona ({pendingPoints.length} vértices)</h2>
              <input
                placeholder="Nombre de la zona"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
              <select
                value={form.zone_type}
                onChange={(e) => {
                  const t = e.target.value as Zone["zone_type"];
                  setForm({ ...form, zone_type: t, color: zoneColors[t] || "#ef4444" });
                }}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="restricted">Restringida (no_entry)</option>
                <option value="monitored">Monitoreada (zone_abandoned)</option>
                <option value="required_presence">Presencia requerida</option>
              </select>
              <div className="flex gap-2 justify-end">
                <button onClick={() => { setShowForm(false); setPendingPoints([]); }} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">Cancelar</button>
                <button onClick={handleSaveZone} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">Guardar zona</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
