"use client";

import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { alerts as alertsApi } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { cn, formatDate, severityColor, statusColor } from "@/lib/utils";

export default function HistoryPage() {
  const [alertList, setAlertList] = useState<Alert[]>([]);

  useEffect(() => {
    alertsApi.list().then((r) => setAlertList(r.data)).catch(() => {});
  }, []);

  return (
    <AppShell>
      <Topbar title="Historial de Eventos" />
      <div className="p-6">
        {alertList.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-gray-400">
            <History className="h-12 w-12 mb-3" />
            <p>Sin eventos registrados</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-500">Fecha</th>
                  <th className="px-4 py-3 font-medium text-gray-500">Tipo</th>
                  <th className="px-4 py-3 font-medium text-gray-500">Descripción</th>
                  <th className="px-4 py-3 font-medium text-gray-500">Severidad</th>
                  <th className="px-4 py-3 font-medium text-gray-500">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {alertList.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatDate(a.triggered_at)}</td>
                    <td className="px-4 py-3">{a.alert_type}</td>
                    <td className="px-4 py-3 text-gray-700">{a.description || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={cn("px-2 py-0.5 text-xs font-medium rounded-full", severityColor(a.severity))}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("px-2 py-0.5 text-xs font-medium rounded-full", statusColor(a.status))}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
