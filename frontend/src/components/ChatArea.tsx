"use client";

import React, { useEffect, useRef, useState } from "react";
import { Message } from "@/types";
import { AdvisoryCard } from "./AdvisoryCard";
import {
  Send,
  CloudSun,
  User,
  Bot,
  Loader2,
  Sparkles,
  AlertTriangle,
} from "lucide-react";

interface ChatAreaProps {
  messages: Message[];
  onSend: (query: string) => Promise<void>;
  loading: boolean;
  error: string | null;
  conversationTitle?: string;
}

const STARTER_PROMPTS = [
  "Can I cycle in Bangalore today?",
  "Can I go for an outdoor workout in Delhi?",
  "Is it a good day for a picnic in Bangalore?",
  "Can my toddler play at the park in Mumbai?",
];

export function ChatArea({
  messages,
  onSend,
  loading,
  error,
  conversationTitle,
}: ChatAreaProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput("");
    await onSend(query);
  };

  const handleStarterClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50 overflow-hidden relative">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-3 sm:px-6 md:px-8 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {messages.length === 0 ? (
          <div className="h-full min-h-[360px] flex flex-col items-center justify-center max-w-lg mx-auto text-center py-6 sm:py-12 px-2">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-sky-500/10 border border-sky-200 flex items-center justify-center text-sky-600 mb-3 sm:mb-4 shadow-xs">
              <CloudSun className="w-8 h-8 sm:w-9 sm:h-9" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-800 tracking-tight">
              Safety Advisory Consultation
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1.5 sm:mt-2 mb-6 sm:mb-8 leading-relaxed max-w-md">
              Ask any outdoor weather question. Queries are geocoded, live weather is retrieved from Open-Meteo, and strictly evaluated against official Standard Operating Procedures.
            </p>

            <div className="w-full space-y-2">
              <div className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 sm:mb-3 flex items-center justify-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-sky-500" />
                <span>Example Scenarios</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleStarterClick(prompt)}
                    className="p-2.5 sm:p-3 bg-white hover:bg-sky-50/60 active:bg-sky-100 rounded-xl border border-slate-200/80 text-xs font-medium text-slate-700 hover:text-sky-700 hover:border-sky-300 transition text-left shadow-xs flex items-center"
                  >
                    &ldquo;{prompt}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className={`flex gap-2.5 sm:gap-3 md:gap-4 ${
                  isUser ? "justify-end" : "justify-start"
                }`}
              >
                {!isUser && (
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-900 text-sky-400 flex items-center justify-center flex-shrink-0 shadow-xs mt-1">
                    <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </div>
                )}

                <div className={`space-y-1 max-w-[92%] sm:max-w-[85%] md:max-w-2xl ${isUser ? "items-end" : "items-start w-full"}`}>
                  {isUser ? (
                    <div className="bg-sky-600 text-white rounded-2xl rounded-tr-xs px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs sm:text-sm font-medium shadow-md shadow-sky-600/10 break-words">
                      {msg.content}
                    </div>
                  ) : (
                    <AdvisoryCard
                      content={msg.content}
                      weather={msg.advisory_record?.weather_metrics}
                      selectedSop={msg.advisory_record?.selected_sop}
                      matchedSops={msg.advisory_record?.matched_sops}
                      severity={msg.advisory_record?.severity}
                      location={msg.advisory_record?.location}
                      activity={msg.advisory_record?.activity}
                    />
                  )}
                </div>

                {isUser && (
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Loading / Generating State */}
        {loading && (
          <div className="flex gap-2.5 sm:gap-3 items-start">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-900 text-sky-400 flex items-center justify-center flex-shrink-0 shadow-xs mt-1">
              <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </div>
            <div className="bg-white border border-slate-200/90 rounded-2xl rounded-tl-xs p-3.5 sm:p-4 shadow-xs flex items-center gap-2.5 sm:gap-3 text-xs font-medium text-slate-600">
              <Loader2 className="w-4 h-4 animate-spin text-sky-500 flex-shrink-0" />
              <span>Fetching live weather & evaluating deterministic SOP rules...</span>
            </div>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-500" />
            <span className="break-words">{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-2.5 sm:p-4 bg-white/95 border-t border-slate-200 backdrop-blur-md flex-shrink-0">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask about weather safety (e.g. 'Can I cycle in Bangalore today?')..."
            className="flex-1 px-3.5 sm:px-4 py-2.5 sm:py-3 bg-slate-100/90 hover:bg-slate-100 focus:bg-white border border-slate-200 rounded-xl sm:rounded-2xl text-slate-900 placeholder-slate-400 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2.5 sm:p-3 bg-sky-600 hover:bg-sky-500 text-white rounded-xl sm:rounded-2xl font-semibold shadow-md shadow-sky-600/20 transition disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 flex-shrink-0 flex items-center justify-center min-w-[40px] min-h-[40px] sm:min-w-[48px] sm:min-h-[48px]"
            title="Send query"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
            ) : (
              <Send className="w-4 h-4 sm:w-5 sm:h-5" />
            )}
          </button>
        </form>
        <div className="text-[10px] sm:text-[11px] text-center text-slate-400 mt-1.5 sm:mt-2 hidden sm:block">
          Safety policies are deterministic. LLM explanations are strictly grounded in live weather data.
        </div>
      </div>
    </div>
  );
}
