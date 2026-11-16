"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCircle, Eye, ImageIcon, Trash2, X, XCircle } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { useAuth } from "@/context/auth-context";
import { alerts as alertsApi } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { cn, formatDate, severityColor, statusColor } from "@/lib/utils";

export default function AlertsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [deleting, setDeleting] = useState(false);
  const [alertList, setAlertList] = useState<Alert[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [photo, setPhoto] = useState<{ url: string; alert: Alert } | null>(null);

  const openPhoto = async (a: Alert) => {
    const res = await alertsApi.snapshot(a.id);
    setPhoto({ url: URL.createObjectURL(res.data), alert: a });
  };

  const closePhoto = () => {
    if (photo) URL.revokeObjectURL(photo.url);
    setPhoto(null);
  };

  const load = useCallback(() => {
    const params: Record<string, string> = {};
    if (statusFilter !== "all") params.status = statusFilter;
    alertsApi.list(params).then((r) => setAlertList(r.data)).catch(() => {});
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (id: string, status: string) => {
    await alertsApi.update(id, { status });
    load();
  };

  const deleteAlert = async (id: string) => {
    if (!isAdmin || deleting || !window.confirm("¿Eliminar permanentemente esta alerta y su captura?")) return;
    setDeleting(true);
    try {
      await alertsApi.delete(id);
      if (photo?.alert.id === id) closePhoto();
      load();
    } catch {
      window.alert("No se pudo eliminar la alerta y su imagen. Intenta nuevamente.");
    } finally {
      setDeleting(false);
    }
  };

  const handleCleanup = async () => {
    if (!isAdmin || deleting) return;
    const input = window.prompt("Días de antigüedad para depurar alertas y fotos (1 a 365):", "30");
    if (input === null) return;
    const days = Number(input);
    if (!Number.isInteger(days) || days < 1 || days > 365) {
      window.alert("Ingresa un número entero entre 1 y 365.");
      return;
    }
    if (!window.confirm(`¿Eliminar permanentemente las alertas y fotos anteriores a ${days} días?`)) return;
    setDeleting(true);
    try {
      const res = await alertsApi.cleanup(days);
      closePhoto();
      window.alert(res.data.message);
      load();
    } catch {
      window.alert("No se pudo depurar el historial.");
    } finally {
      setDeleting(false);
    }
  };

  const filters = [
    { value: "all", label: "Todas" },
    { value: "new", label: "Nuevas" },
    { value: "acknowledged", label: "Revisadas" },
    { value: "resolved", label: "Resueltas" },
    { value: "false_alarm", label: "Falsas alarmas" },
  ];

  return (
    <AppShell>
      <Topbar title="Centro de Alertas" />
      <div className="p-6">
        {/* Filters */}
        <div className="flex items-center justify-between gap-2 mb-6 flex-wrap">
          <div className="flex gap-2">
            {filters.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={cn(
                  "px-3 py-1.5 text-sm rounded-lg transition-colors",
                  statusFilter === f.value
                    ? "bg-blue-600 text-white"
                    : "bg-white border text-gray-600 hover:bg-gray-50"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          {isAdmin && <button
            disabled={deleting}
            onClick={handleCleanup}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors ml-auto"
            title="Depurar alertas y fotos antiguas para ahorrar espacio"
          >
            <Trash2 className="h-3.5 w-3.5" /> Depurar historial antiguo
          </button>}
        </div>

        {/* Alert list */}
        {alertList.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-gray-400">
            <Bell className="h-12 w-12 mb-3" />
            <p>No hay alertas con este filtro</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alertList.map((a) => (
              <div key={a.id} className="bg-white rounded-xl border p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn("px-2 py-0.5 text-xs font-medium rounded-full", severityColor(a.severity))}>
                        {a.severity}
                      </span>
                      <span className={cn("px-2 py-0.5 text-xs font-medium rounded-full", statusColor(a.status))}>
                        {a.status}
                      </span>
                    </div>
                    <p className="font-medium text-gray-900">{a.description || a.alert_type}</p>
                    <p className="text-sm text-gray-500 mt-1">{formatDate(a.triggered_at)}</p>
                  </div>

                  <div className="flex gap-1 ml-4">
                    {a.has_snapshot && (
                      <button
                        onClick={() => openPhoto(a)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                        title="Ver foto del momento"
                      >
                        <ImageIcon className="h-4 w-4" />
                      </button>
                    )}
                    {a.status === "new" && (
                      <button
                        onClick={() => updateStatus(a.id, "acknowledged")}
                        className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg"
                        title="Marcar como revisada"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    )}
                    {(a.status === "new" || a.status === "acknowledged") && (
                      <>
                        <button
                          onClick={() => updateStatus(a.id, "resolved")}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                          title="Resolver"
                        >
                          <CheckCircle className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => updateStatus(a.id, "false_alarm")}
                          className="p-2 text-gray-500 hover:bg-gray-50 rounded-lg"
                          title="Falsa alarma"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    {isAdmin && <button
                      disabled={deleting}
                      onClick={() => deleteAlert(a.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                      title="Eliminar alerta y foto"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {photo && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={closePhoto}>
            <div className="bg-white rounded-xl p-4 max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-medium text-gray-900">{photo.alert.description}</p>
                  <p className="text-sm text-gray-500">{formatDate(photo.alert.triggered_at)}</p>
                </div>
                <button onClick={closePhoto} className="p-1 text-gray-400 hover:text-gray-700">
                  <X className="h-5 w-5" />
                </button>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo.url} alt="Foto de la alerta" className="w-full rounded-lg" />
              <p className="text-xs text-gray-500 mt-3">
                Este aviso es para revisión, no una acusación: la decisión final la toma una persona.
              </p>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
