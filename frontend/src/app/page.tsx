"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { ConversationSummary, Message, AdvisoryRecord } from "@/types";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  const { user, token, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Redirect unauthenticated users
  useEffect(() => {
    if (!authLoading && !token) {
      router.push("/login");
    }
  }, [authLoading, token, router]);

  // Load user conversation list
  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      setConversationsLoading(true);
      const list = await api.listConversations(token);
      setConversations(list);
    } catch (err: any) {
      console.error("Failed to load conversations:", err);
    } finally {
      setConversationsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchConversations();
    }
  }, [token, fetchConversations]);

  // Load a specific conversation's thread
  const handleSelectConversation = async (id: string) => {
    if (!token) return;
    setActiveId(id);
    setError(null);
    try {
      setQueryLoading(true);
      const detail = await api.getConversation(token, id);

      // Pair advisory records with assistant messages
      const advisoryMap = new Map<number, AdvisoryRecord>();
      (detail.advisory_records || []).forEach((rec, idx) => {
        advisoryMap.set(idx, rec);
      });

      let assistantIdx = 0;
      const mappedMessages = detail.messages.map((m) => {
        if (m.role === "assistant") {
          const rec = (detail.advisory_records || [])[assistantIdx];
          assistantIdx++;
          return {
            ...m,
            advisory_record: rec,
          };
        }
        return m;
      });

      setMessages(mappedMessages);
    } catch (err: any) {
      setError(err.message || "Failed to load conversation messages.");
    } finally {
      setQueryLoading(false);
    }
  };

  // Start a fresh consultation
  const handleNewChat = () => {
    setActiveId(null);
    setMessages([]);
    setError(null);
  };

  // Delete a conversation
  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!token) return;
    try {
      await api.deleteConversation(token, id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        handleNewChat();
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete conversation.");
    }
  };

  // Send a user query
  const handleSendQuery = async (queryText: string) => {
    if (!token) return;
    setError(null);

    // Optimistic user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeId || "",
      role: "user",
      content: queryText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setQueryLoading(true);

    try {
      const response = await api.postAdvisory(queryText, activeId, token);

      const targetConvId = response.conversation_id;
      setActiveId(targetConvId);

      const responseText = response.response || response.message || "";

      // Build structured advisory record for UI rendering
      const record: AdvisoryRecord = {
        id: `rec-${Date.now()}`,
        conversation_id: targetConvId,
        user_query: queryText,
        location: response.resolved_location_name || response.location,
        activity: response.activity,
        person_context: response.person_context,
        selected_sop: response.selected_sop,
        matched_sops: response.matched_sops,
        severity: response.severity || response.selected_sop?.severity,
        weather_metrics: response.weather,
        generated_response: responseText,
        created_at: new Date().toISOString(),
      };

      const assistantMsg: Message = {
        id: `msg-${Date.now()}`,
        conversation_id: targetConvId,
        role: "assistant",
        content: responseText,
        created_at: new Date().toISOString(),
        advisory_record: record,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh sidebar conversation list
      await fetchConversations();
    } catch (err: any) {
      setError(err.message || "Failed to process advisory query.");
      // Rollback optimistic user message on complete network error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setQueryLoading(false);
    }
  };

  if (authLoading || (!token && typeof window !== "undefined")) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-slate-300">
        <Loader2 className="w-8 h-8 animate-spin text-sky-400 mb-3" />
        <p className="text-sm font-medium">Loading session...</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100 overflow-hidden">
      <Header
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        sidebarOpen={sidebarOpen}
      />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={handleSelectConversation}
          onNewChat={handleNewChat}
          onDelete={handleDeleteConversation}
          loading={conversationsLoading}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          <ChatArea
            messages={messages}
            onSend={handleSendQuery}
            loading={queryLoading}
            error={error}
          />
        </main>
      </div>
    </div>
  );
}
