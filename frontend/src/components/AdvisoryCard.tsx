"use client";

import React from "react";
import { SOP, WeatherMetrics } from "@/types";
import {
  Thermometer,
  Wind,
  CloudRain,
  Sun,
  Droplets,
  ShieldAlert,
  ShieldCheck,
  Info,
} from "lucide-react";

interface AdvisoryCardProps {
  content: string;
  weather?: WeatherMetrics;
  selectedSop?: SOP | null;
  matchedSops?: SOP[];
  severity?: string | null;
  location?: string | null;
  activity?: string | null;
}

export function AdvisoryCard({
  content,
  weather,
  selectedSop,
  matchedSops = [],
  severity,
  location,
  activity,
}: AdvisoryCardProps) {
  const getSeverityBadge = (sev?: string | null) => {
    switch (sev?.toUpperCase()) {
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
            <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-rose-500 animate-pulse" />
            HIGH RISK
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-amber-500" />
            MEDIUM RISK
          </span>
        );
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-500" />
            LOW RISK / ADVISORY
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            No SOP Guideline
          </span>
        );
    }
  };

  const hasMatchedSop = !!selectedSop || (matchedSops && matchedSops.length > 0);
  const additionalSops = (matchedSops || []).filter(
    (sop) => !selectedSop || sop.id !== selectedSop.id
  );

  const isHistorical =
    weather?.is_historical ||
    (weather?.forecast_window && weather.forecast_window.toLowerCase().includes("yesterday"));

  return (
    <div className="space-y-3 sm:space-y-4 max-w-2xl w-full">
      {/* 1. FACTUAL WEATHER METRICS PANEL */}
      {weather && (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-3 sm:p-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2.5 sm:pb-3 border-b border-slate-100 mb-2.5 sm:mb-3 gap-2">
            <div className="flex items-center gap-2 text-[11px] sm:text-xs font-bold uppercase tracking-wider text-slate-500">
              <Sun className="w-4 h-4 text-amber-500 flex-shrink-0" />
              <span>
                {isHistorical
                  ? "Observed Historical Weather"
                  : weather.forecast_window
                  ? "Forecast Weather Facts"
                  : "Observed Weather Facts"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              {weather.forecast_window && (
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                    isHistorical
                      ? "text-amber-700 bg-amber-50 border-amber-200"
                      : "text-sky-600 bg-sky-50 border-sky-200"
                  }`}
                >
                  {weather.forecast_window}
                </span>
              )}
              {location && (
                <span className="text-[11px] sm:text-xs font-semibold text-slate-700 bg-slate-100 px-2 sm:px-2.5 py-0.5 rounded-full">
                  {location}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
            {weather.temperature !== undefined && (
              <div className="bg-slate-50/80 rounded-xl p-2 sm:p-2.5 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] sm:text-[11px] font-medium">
                  <Thermometer className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
                  <span>Temp</span>
                </div>
                <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 sm:mt-1">
                  {weather.temperature}°C
                </div>
              </div>
            )}

            {weather.wind_speed !== undefined && (
              <div className="bg-slate-50/80 rounded-xl p-2 sm:p-2.5 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] sm:text-[11px] font-medium">
                  <Wind className="w-3.5 h-3.5 text-sky-500 flex-shrink-0" />
                  <span>Wind</span>
                </div>
                <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 sm:mt-1">
                  {weather.wind_speed} <span className="text-[10px] sm:text-xs font-normal">km/h</span>
                </div>
              </div>
            )}

            {weather.precipitation_probability !== undefined && (
              <div className="bg-slate-50/80 rounded-xl p-2 sm:p-2.5 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] sm:text-[11px] font-medium">
                  <CloudRain className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
                  <span>Rain Prob</span>
                </div>
                <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 sm:mt-1">
                  {weather.precipitation_probability}%
                </div>
              </div>
            )}

            {weather.uv_index !== undefined && (
              <div className="bg-slate-50/80 rounded-xl p-2 sm:p-2.5 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] sm:text-[11px] font-medium">
                  <Sun className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span>UV Index</span>
                </div>
                <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 sm:mt-1">
                  {weather.uv_index}
                </div>
              </div>
            )}

            {weather.relative_humidity !== undefined && (
              <div className="bg-slate-50/80 rounded-xl p-2 sm:p-2.5 border border-slate-100 col-span-2 sm:col-span-1">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] sm:text-[11px] font-medium">
                  <Droplets className="w-3.5 h-3.5 text-teal-500 flex-shrink-0" />
                  <span>Humidity</span>
                </div>
                <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 sm:mt-1">
                  {weather.relative_humidity}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. DETERMINISTIC SAFETY ASSESSMENT */}
      {hasMatchedSop && selectedSop ? (
        <div className="bg-white rounded-2xl border-2 border-slate-200 p-3.5 sm:p-5 shadow-xs space-y-3 sm:space-y-4">
          <div className="flex items-start justify-between gap-2.5 sm:gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-900 text-white">
                  {selectedSop.id}
                </span>
                <h3 className="text-sm sm:text-base font-bold text-slate-900">
                  {selectedSop.name}
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Category: <span className="font-medium text-slate-700">{selectedSop.category}</span>
              </p>
            </div>
            <div>{getSeverityBadge(selectedSop.severity || severity)}</div>
          </div>

          {/* Official Recommendation Callout */}
          <div className="p-3 sm:p-4 rounded-xl bg-slate-900 text-white shadow-inner">
            <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-sky-400 mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-sky-400 flex-shrink-0" />
              <span>Authoritative SOP Directive</span>
            </div>
            <p className="text-xs sm:text-sm font-medium leading-relaxed">
              {selectedSop.advice}
            </p>
          </div>

          {/* Additional Matched Guidelines */}
          {additionalSops.length > 0 && (
            <div className="pt-2.5 sm:pt-3 border-t border-slate-100">
              <div className="text-[11px] sm:text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Additional Concurrent SOP Matches:</span>
              </div>
              <div className="space-y-1.5 sm:space-y-2">
                {additionalSops.map((sop) => (
                  <div
                    key={sop.id}
                    className="p-2 sm:p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs gap-2"
                  >
                    <div className="truncate">
                      <span className="font-mono font-bold text-slate-700 mr-2">
                        {sop.id}
                      </span>
                      <span className="text-slate-900 font-medium">{sop.name}</span>
                    </div>
                    <span className="font-semibold text-slate-500 uppercase text-[10px] flex-shrink-0">
                      {sop.severity}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* NO-GUIDANCE GUARDRAIL DISPLAY */
        <div className="bg-slate-50 rounded-2xl border border-slate-200 p-3 sm:p-4 space-y-2">
          <div className="flex items-center gap-2 text-[11px] sm:text-xs font-bold uppercase tracking-wider text-slate-500">
            <ShieldCheck className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span>Policy Assessment</span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-slate-500">Applicable SOP:</span>
            <span className="text-xs font-semibold text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded">
              None
            </span>
            <span className="text-xs font-medium text-slate-500 ml-1 sm:ml-2">Severity:</span>
            <span className="text-xs font-semibold text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded">
              None
            </span>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed bg-white p-2.5 sm:p-3 rounded-xl border border-slate-200/60">
            No formal Standard Operating Procedure (SOP) guideline applies to this activity under the observed weather conditions. In accordance with strict safety protocols, no safety clearance or generic recommendation is provided.
          </p>
        </div>
      )}

      {/* 3. GENERATED NATURAL LANGUAGE EXPLANATION */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-3.5 sm:p-4 shadow-xs text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap break-words">
        {content}
      </div>
    </div>
  );
}
