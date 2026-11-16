"use client";

import { useEffect, useState } from "react";
import { notifications, type NotificationConfig } from "@/lib/api";
import { AppShell } from "@/components/layout/app-shell";
import { Topbar } from "@/components/layout/topbar";
import { useAuth } from "@/context/auth-context";
import { Shield, Bell, Users, Building } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  const [configuration, setConfiguration] = useState<{ userId: string; data: NotificationConfig | null } | null>(null);
  useEffect(() => {
    if (!user || user.role !== "admin") return;
    let active = true;
    notifications.config()
      .then(({ data }) => { if (active) setConfiguration({ userId: user.id, data }); })
      .catch(() => { if (active) setConfiguration({ userId: user.id, data: null }); });
    return () => { active = false; };
  }, [user]);
  const current = configuration?.userId === user?.id ? configuration : null;
  const config = current?.data;
  const notificationStatus = user?.role !== "admin" ? "Consultar con el administrador"
    : !current ? "Consultando configuración…"
    : !config ? "No se pudo consultar"
    : config.channel === "disabled" ? "Desactivado"
    : config.test_mode ? "Modo de prueba: sin envíos"
    : !config.credentials_configured ? "Faltan credenciales"
    : !config.recipient_configured ? "Falta configurar destinatario"
    : "Configurado para envíos reales";


  const sections = [
    {
      title: "Restaurante",
      icon: Building,
      description: "Información general del establecimiento",
      fields: [
        { label: "Nombre", value: "Restaurante Demo" },
        { label: "Zona horaria", value: "America/Bogota" },
        { label: "Plan", value: "professional" },
      ],
    },
    {
      title: "Notificaciones",
      icon: Bell,
      description: "Estado de la configuración de alertas",
      fields: [
        { label: "Canal", value: config?.channel || "Sin verificar" },
        { label: "Estado", value: notificationStatus },
        { label: "Chat ID", value: user?.telegram_chat_id || "No configurado" },
      ],
    },
    {
      title: "Mi perfil",
      icon: Users,
      description: "Información de tu cuenta",
      fields: [
        { label: "Email", value: user?.email || "" },
        { label: "Nombre", value: user?.full_name || "No configurado" },
        { label: "Rol", value: user?.role || "" },
      ],
    },
    {
      title: "Seguridad",
      icon: Shield,
      description: "Protección de datos y cumplimiento",
      fields: [
        { label: "Ley 1581 de 2012", value: "Política de tratamiento activa" },
        { label: "Depuración manual de snapshots", value: config ? `A partir de ${config.retention_days} días` : "Consultar con el administrador" },
        { label: "Reconocimiento facial", value: "No implementado (fase futura)" },
      ],
    },
  ];

  return (
    <AppShell>
      <Topbar title="Configuración" />
      <div className="p-6 max-w-3xl space-y-6">
        {sections.map((s) => (
          <div key={s.title} className="bg-white rounded-xl border">
            <div className="flex items-center gap-3 px-5 py-4 border-b">
              <s.icon className="h-5 w-5 text-gray-400" />
              <div>
                <h2 className="font-semibold text-gray-900">{s.title}</h2>
                <p className="text-sm text-gray-500">{s.description}</p>
              </div>
            </div>
            <div className="divide-y">
              {s.fields.map((f) => (
                <div key={f.label} className="flex items-center justify-between px-5 py-3">
                  <span className="text-sm text-gray-500">{f.label}</span>
                  <span className="text-sm font-medium text-gray-900">{f.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
