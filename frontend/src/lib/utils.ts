import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("es-CO", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "text-red-600 bg-red-50";
    case "high": return "text-orange-600 bg-orange-50";
    case "medium": return "text-yellow-600 bg-yellow-50";
    case "low": return "text-blue-600 bg-blue-50";
    default: return "text-gray-600 bg-gray-50";
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case "online": return "text-green-600";
    case "offline": return "text-gray-400";
    case "error": return "text-red-600";
    case "new": return "text-red-600 bg-red-50";
    case "acknowledged": return "text-yellow-600 bg-yellow-50";
    case "resolved": return "text-green-600 bg-green-50";
    case "false_alarm": return "text-gray-500 bg-gray-50";
    default: return "text-gray-600";
  }
}
