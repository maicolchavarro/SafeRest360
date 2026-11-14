"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { ZoneCanvas } from "@/components/zones/zone-canvas";
import { cameras as camerasApi, zones as zonesApi } from "@/lib/api";
import type { Camera, Zone, PolygonPoint } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";

export default function CameraDetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>}>
      <CameraDetailInner />
    </Suspense>
  );
}

function CameraDetailInner() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [camera, setCamera] = useState<Camera | null>(null);
  const [zoneList, setZoneList] = useState<Zone[]>([]);
  const [activeZone, setActiveZone] = useState<string | undefined>();
  const [drawing, setDrawing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<{ name: string; zone_type: Zone["zone_type"]; color: string }>({ name: "", zone_type: "restricted", color: "#ef4444" });
  const [pendingPoints, setPendingPoints] = useState<PolygonPoint[]>([]);

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
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Canvas area */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl border p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">Zonas de vigilancia</h2>
                {user?.role === "admin" && (
                  <button
                    onClick={() => setDrawing(!drawing)}
                    className={cn(
                      "flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg",
                      drawing ? "bg-red-100 text-red-700" : "bg-blue-600 text-white hover:bg-blue-700"
                    )}
                  >
                    {drawing ? "Cancelar dibujo" : <><Plus className="h-4 w-4" /> Nueva zona</>}
                  </button>
                )}
              </div>
              {drawing && (
                <p className="text-sm text-blue-600 mb-2">
                  Haz clic para agregar vértices. Doble clic para cerrar el polígono. Clic derecho para deshacer.
                </p>
              )}
              <ZoneCanvas
                width={640}
                height={480}
                zones={zoneList}
                activeZoneId={activeZone}
                drawing={drawing}
                onDrawComplete={handleDrawComplete}
              />
            </div>
          </div>

          {/* Zone list */}
          <div className="space-y-4">
            <div className="bg-white rounded-xl border p-4">
              <h2 className="font-semibold mb-3">Zonas ({zoneList.length})</h2>
              {zoneList.length === 0 ? (
                <p className="text-sm text-gray-500">No hay zonas configuradas</p>
              ) : (
                <div className="space-y-2">
                  {zoneList.map((z) => (
                    <div
                      key={z.id}
                      className={cn(
                        "p-3 rounded-lg border cursor-pointer transition-colors",
                        activeZone === z.id ? "border-blue-500 bg-blue-50" : "hover:bg-gray-50"
                      )}
                      onClick={() => setActiveZone(activeZone === z.id ? undefined : z.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: z.color }} />
                          <span className="text-sm font-medium">{z.name}</span>
                        </div>
                        {user?.role === "admin" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteZone(z.id); }}
                            className="p-1 text-gray-400 hover:text-red-600"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{z.zone_type} · {z.polygon_points.length} vértices</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

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
