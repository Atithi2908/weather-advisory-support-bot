"use client";

import React from "react";
import { ConversationSummary } from "@/types";
import { Plus, MessageSquare, Trash2, Loader2, X } from "lucide-react";

interface SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
  loading: boolean;
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  loading,
  isOpen = false,
  onClose,
}: SidebarProps) {
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "";
    }
  };

  const handleItemClick = (id: string) => {
    onSelect(id);
    if (onClose) onClose();
  };

  const handleNewChatClick = () => {
    onNewChat();
    if (onClose) onClose();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-40 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar / Drawer Container */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-50 md:z-auto
          w-72 sm:w-80 md:w-64 lg:w-72 bg-slate-900 text-slate-300 flex flex-col
          h-full md:h-[calc(100vh-4rem)] border-r border-slate-800 flex-shrink-0
          transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
          shadow-2xl md:shadow-none
        `}
      >
        {/* Mobile Drawer Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 md:hidden">
          <span className="text-sm font-bold text-white tracking-tight">Conversations</span>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Button */}
        <div className="p-3 sm:p-4 border-b border-slate-800">
          <button
            onClick={handleNewChatClick}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs sm:text-sm font-semibold shadow-md transition shadow-sky-950/20 active:scale-[0.99]"
          >
            <Plus className="w-4 h-4" />
            <span>New Consultation</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2.5 sm:p-3 space-y-1">
          <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
            <span>Previous History</span>
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />}
          </div>

          {conversations.length === 0 && !loading ? (
            <div className="p-4 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl my-2">
              <MessageSquare className="w-6 h-6 mx-auto mb-2 text-slate-600" />
              No previous conversations.
              <div className="mt-1 text-slate-600">Start a new query above!</div>
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeId;
              return (
                <div
                  key={conv.id}
                  onClick={() => handleItemClick(conv.id)}
                  className={`group relative flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-sm transition ${
                    isActive
                      ? "bg-slate-800 text-white font-medium shadow-sm border border-slate-700/80"
                      : "hover:bg-slate-800/60 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-6">
                    <MessageSquare
                      className={`w-4 h-4 flex-shrink-0 ${
                        isActive ? "text-sky-400" : "text-slate-500"
                      }`}
                    />
                    <div className="truncate">
                      <span className="block truncate text-xs sm:text-sm">
                        {conv.title || "Weather Query"}
                      </span>
                      <span className="block text-[10px] text-slate-500 mt-0.5">
                        {formatDate(conv.updated_at || conv.created_at)}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => onDelete(conv.id, e)}
                    title="Delete conversation"
                    className="opacity-70 md:opacity-0 group-hover:opacity-100 p-1.5 hover:text-rose-400 rounded-lg hover:bg-slate-700/60 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800/80 text-[11px] text-slate-500 text-center flex-shrink-0">
          12 Authoritative Safety Policies Loaded
        </div>
      </aside>
    </>
  );
}
