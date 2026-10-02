"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { CloudSun, LogOut, ShieldCheck, User as UserIcon, Menu } from "lucide-react";

interface HeaderProps {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export function Header({ onToggleSidebar, sidebarOpen }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between sticky top-0 z-30 flex-shrink-0">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-2 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl md:hidden transition flex-shrink-0"
            aria-label="Toggle navigation menu"
            title="Toggle chat history"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-sky-500/10 border border-sky-200 flex items-center justify-center text-sky-600 shadow-xs flex-shrink-0">
          <CloudSun className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <h1 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight truncate">
              Weather Safety Assistant
            </h1>
            <span className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80 flex-shrink-0">
              <ShieldCheck className="w-3 h-3 text-emerald-600" />
              <span className="hidden xs:inline">SOP Governed</span>
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-500 hidden md:block truncate">
            Deterministic Outdoor Activity Safety Guidance
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
        {user && (
          <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-slate-600 bg-slate-100/80 px-3 py-1.5 rounded-full border border-slate-200/60 max-w-[200px]">
            <UserIcon className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <span className="truncate">{user.email}</span>
          </div>
        )}

        <button
          onClick={logout}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-rose-600 hover:bg-rose-50 px-2.5 sm:px-3 py-2 rounded-xl transition border border-transparent hover:border-rose-200"
          title="Sign out of your account"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
