"use client";

import { Bell, User } from "lucide-react";
import { useAuth } from "@/context/auth-context";

export function Topbar({ title }: { title: string }) {
  const { user } = useAuth();

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-white border-b">
      <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
      <div className="flex items-center gap-4">
        <button className="relative p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
        </button>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <User className="h-5 w-5" />
          <span>{user?.full_name || user?.email}</span>
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
            {user?.role}
          </span>
        </div>
      </div>
    </header>
  );
}
