"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, Plus, Wifi, WifiOff, AlertCircle, Pencil, Trash2, MapPin, Eye } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { cameras as camerasApi } from "@/lib/api";
import type { Camera as CameraType } from "@/lib/types";
import { cn, statusColor, formatDate } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";

const statusIcons = { online: Wifi, offline: WifiOff, error: AlertCircle };

export default function CamerasPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [cameraList, setCameraList] = useState<CameraType[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", location_description: "", rtsp_url: "", stream_type: "rtsp", fps: 15 });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const load = () => camerasApi.list().then((r) => setCameraList(r.data)).catch(() => {});

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setForm({ name: "", location_description: "", rtsp_url: "", stream_type: "rtsp", fps: 15 });
    setEditId(null);
    setShowForm(false);
    setError("");
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    setSaving(true);
    setError("");
    try {
      // the API never returns the stored URL, so an empty field on edit means "keep it"
      const { rtsp_url, ...rest } = form;
      const payload = rtsp_url.trim() ? { ...rest, rtsp_url: rtsp_url.trim() } : rest;
      if (editId) {
        await camerasApi.update(editId, payload);
      } else {
        await camerasApi.create(payload);
      }
      resetForm();
      load();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      const msg = Array.isArray(detail) ? (detail[0] as { msg?: string })?.msg : undefined;
      setError(msg ? msg.replace(/^Value error, /, "") : "Error al guardar la cámara");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (e: React.MouseEvent, c: CameraType) => {
    e.stopPropagation();
    setEditId(c.id);
    setForm({ name: c.name, location_description: c.location_description || "", rtsp_url: "", stream_type: c.stream_type, fps: c.fps });
    setShowForm(true);
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    await camerasApi.delete(deleteConfirm);
    setDeleteConfirm(null);
    load();
  };

  return (
    <AppShell>
      <Topbar title="Cámaras" />
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <p className="text-gray-500">{cameraList.length} cámaras registradas</p>
          {user?.role === "admin" && (
            <button
              onClick={() => { setShowForm(true); setEditId(null); setError(""); }}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <Plus className="h-4 w-4" /> Agregar cámara
            </button>
          )}
        </div>

        {/* Empty state */}
        {cameraList.length === 0 && !showForm && (
          <div className="flex flex-col items-center py-16 text-gray-400">
            <Camera className="h-16 w-16 mb-4" />
            <p className="text-lg mb-1">Sin cámaras registradas</p>
            <p className="text-sm mb-4">Agrega tu primera cámara para comenzar a configurar zonas y reglas.</p>
            {user?.role === "admin" && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                <Plus className="h-4 w-4" /> Agregar primera cámara
              </button>
            )}
          </div>
        )}

        {/* Form modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-4">
              <h2 className="text-lg font-semibold">{editId ? "Editar" : "Nueva"} cámara</h2>

              {error && (
                <div className="p-3 text-sm text-red-700 bg-red-50 rounded-lg">{error}</div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                <input
                  placeholder="Ej: Entrada principal"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
                <input
                  placeholder="Ej: Primer piso, junto a la puerta"
                  value={form.location_description}
                  onChange={(e) => setForm({ ...form, location_description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL del stream</label>
                <input
                  placeholder="rtsp://192.168.1.100:554/stream1"
                  value={form.rtsp_url}
                  onChange={(e) => setForm({ ...form, rtsp_url: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
                />
                <p className="text-xs text-gray-400 mt-1">
                  {editId && cameraList.find((c) => c.id === editId)?.has_stream_url
                    ? "Ya tiene un stream configurado; deja vacío para mantenerlo"
                    : "rtsp:// o rtsps://. Puedes configurarlo después"}
                </p>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de stream</label>
                  <select
                    value={form.stream_type}
                    onChange={(e) => setForm({ ...form, stream_type: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="rtsp">RTSP</option>
                    <option value="http">HTTP / MJPEG</option>
                    <option value="file">Archivo de video</option>
                  </select>
                </div>
                <div className="w-24">
                  <label className="block text-sm font-medium text-gray-700 mb-1">FPS</label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={form.fps}
                    onChange={(e) => setForm({ ...form, fps: Number(e.target.value) })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button onClick={resetForm} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">
                  Cancelar
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
                >
                  {saving ? "Guardando..." : "Guardar"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete confirmation */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-sm space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Eliminar cámara</h2>
              <p className="text-sm text-gray-600">
                Esta acción desactivará la cámara y todas sus zonas y reglas asociadas. ¿Continuar?
              </p>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">
                  Cancelar
                </button>
                <button onClick={handleDelete} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm">
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Camera grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cameraList.map((c) => {
            const StatusIcon = statusIcons[c.status] || WifiOff;
            return (
              <div
                key={c.id}
                className="bg-white rounded-xl border overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => router.push(`/cameras/${c.id}`)}
              >
                <div className="bg-gray-800 h-40 flex items-center justify-center relative">
                  <Camera className="h-12 w-12 text-gray-500" />
                  <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full bg-black/50 text-xs text-white">
                    <StatusIcon className="h-3 w-3" />
                    {c.status}
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold mb-1">{c.name}</h3>
                  {c.location_description && (
                    <div className="flex items-center gap-1 text-sm text-gray-500 mb-2">
                      <MapPin className="h-3 w-3" />
                      {c.location_description}
                    </div>
                  )}
                  <p className="text-xs text-gray-400">
                    {c.stream_type.toUpperCase()} · {c.fps} FPS
                    {c.last_heartbeat && ` · ${formatDate(c.last_heartbeat)}`}
                  </p>
                  {user?.role === "admin" && (
                    <div className="flex gap-3 mt-3 pt-3 border-t">
                      <button
                        onClick={(e) => { e.stopPropagation(); router.push(`/cameras/${c.id}`); }}
                        className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                      >
                        <Eye className="h-3 w-3" /> Zonas
                      </button>
                      <button
                        onClick={(e) => handleEdit(e, c)}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600"
                      >
                        <Pencil className="h-3 w-3" /> Editar
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(c.id); }}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-600"
                      >
                        <Trash2 className="h-3 w-3" /> Eliminar
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
