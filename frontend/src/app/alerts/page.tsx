"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCircle, Eye, XCircle } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { alerts as alertsApi } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { cn, formatDate, severityColor, statusColor } from "@/lib/utils";

export default function AlertsPage() {
  const [alertList, setAlertList] = useState<Alert[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");

  const load = () => {
    const params: Record<string, string> = {};
    if (statusFilter !== "all") params.status = statusFilter;
    alertsApi.list(params).then((r) => setAlertList(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, [statusFilter]);

  const updateStatus = async (id: string, status: string) => {
    await alertsApi.update(id, { status });
    load();
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
        <div className="flex gap-2 mb-6">
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
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
