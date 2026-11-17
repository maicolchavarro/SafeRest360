"use client";

import { useEffect, useState } from "react";
import {
  Camera,
  Bell,
  AlertTriangle,
  CheckCircle,
  MapPin,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { dashboard, alerts as alertsApi } from "@/lib/api";
import type { DashboardSummary, Alert } from "@/lib/types";
import { cn, formatDate, severityColor, statusColor } from "@/lib/utils";

// Cuenta las alertas reales de hoy (hora local del navegador) en 24 franjas de una hora.
function emptyHourBuckets() {
  return Array.from({ length: 24 }, (_, h) => ({
    hour: `${String(h).padStart(2, "0")}:00`,
    alertas: 0,
  }));
}

// Solo se llama dentro de useEffect, para que la fecha se lea en el navegador y no al prerenderizar.
function alertsPerHourToday(alertList: Alert[]) {
  const buckets = emptyHourBuckets();
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  for (const a of alertList) {
    const t = new Date(a.triggered_at);
    if (!Number.isNaN(t.getTime()) && t >= startOfToday) {
      buckets[t.getHours()].alertas += 1;
    }
  }
  return buckets;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [chartData, setChartData] = useState(emptyHourBuckets);
  const [chartTotal, setChartTotal] = useState(0);

  useEffect(() => {
    dashboard.summary().then((r) => setSummary(r.data)).catch(() => {});
    alertsApi.list({ status: "new" }).then((r) => setRecentAlerts(r.data.slice(0, 5))).catch(() => {});
    alertsApi
      .list({ limit: "200" })
      .then((r) => {
        const data = alertsPerHourToday(r.data);
        setChartData(data);
        setChartTotal(data.reduce((sum, b) => sum + b.alertas, 0));
      })
      .catch(() => {});
  }, []);

  const stats = [
    {
      label: "Cámaras activas",
      value: summary?.cameras_online ?? 0,
      total: summary?.total_cameras ?? 0,
      icon: Camera,
      color: "text-green-600 bg-green-50",
    },
    {
      label: "Alertas hoy",
      value: summary?.alerts_today ?? 0,
      icon: Bell,
      color: "text-blue-600 bg-blue-50",
    },
    {
      label: "Alertas pendientes",
      value: summary?.alerts_pending ?? 0,
      icon: AlertTriangle,
      color: "text-orange-600 bg-orange-50",
    },
    {
      label: "Zonas configuradas",
      value: summary?.zones_configured ?? 0,
      icon: MapPin,
      color: "text-purple-600 bg-purple-50",
    },
  ];

  return (
    <AppShell>
      <Topbar title="Dashboard" />
      <div className="p-6 space-y-6">
        {/* Stats grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} className="bg-white rounded-xl border p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{s.label}</p>
                  <p className="text-2xl font-bold mt-1">
                    {s.value}
                    {s.total !== undefined && (
                      <span className="text-sm font-normal text-gray-400">
                        {" "}/ {s.total}
                      </span>
                    )}
                  </p>
                </div>
                <div className={cn("p-3 rounded-lg", s.color)}>
                  <s.icon className="h-6 w-6" />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alert chart */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-base font-semibold mb-4">Alertas por hora (hoy)</h2>
            {chartTotal === 0 ? (
              <div className="flex flex-col items-center justify-center h-[240px] text-gray-400">
                <Bell className="h-10 w-10 mb-2" />
                <p>Aún no hay alertas hoy</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" fontSize={12} interval={3} />
                  <YAxis fontSize={12} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="alertas" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Recent alerts */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-base font-semibold mb-4">Alertas recientes</h2>
            {recentAlerts.length === 0 ? (
              <div className="flex flex-col items-center py-8 text-gray-400">
                <CheckCircle className="h-10 w-10 mb-2" />
                <p>Sin alertas pendientes</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentAlerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                    <div>
                      <p className="text-sm font-medium">{a.description || a.alert_type}</p>
                      <p className="text-xs text-gray-500">{formatDate(a.triggered_at)}</p>
                    </div>
                    <span className={cn("px-2 py-1 text-xs font-medium rounded-full", severityColor(a.severity))}>
                      {a.severity}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
