"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Search, Loader2, ChevronDown } from "lucide-react";
import toast from "react-hot-toast";
import { triggerScrape, getScrapeStatus } from "@/lib/api";

interface SearchBarProps {
  onScrapeComplete?: () => void;
}

const TIME_FILTERS = [
  { label: "Last 24h", value: "1" },
  { label: "Last 3 days", value: "3" },
  { label: "Last week", value: "7" },
  { label: "Last month", value: "30" },
  { label: "Any time", value: "" },
];

const EXPERIENCE_LEVELS = [
  { label: "Entry (0-2 yrs)", value: "entry" },
  { label: "Mid (3-5 yrs)", value: "mid" },
  { label: "Senior (5-8 yrs)", value: "senior" },
  { label: "Staff+ (8+ yrs)", value: "staff" },
];

export default function SearchBar({ onScrapeComplete }: SearchBarProps) {
  const [keywords, setKeywords] = useState("software engineer");
  const [location, setLocation] = useState("Los Angeles");
  const [maxDays, setMaxDays] = useState("7");
  const [experience, setExperience] = useState("mid");
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keywords.trim() || loading) return;

    setLoading(true);
    setProgress(0);
    setStatusMessage("Starting search...");

    try {
      const result = await triggerScrape(keywords, location, maxDays, experience);
      const searchId = result.search_id;

      // Poll for progress
      pollRef.current = setInterval(async () => {
        try {
          const status = await getScrapeStatus(searchId);
          setProgress(status.progress);
          setStatusMessage(status.message);

          if (status.status === "done" || status.status === "error") {
            stopPolling();
            setLoading(false);

            if (status.status === "done") {
              toast.success(`Found ${status.jobs_found} new jobs!`, { duration: 3000 });
              onScrapeComplete?.();
            } else {
              toast.error("Scrape failed. Try again.");
            }

            // Keep the completed bar visible briefly, then reset
            setTimeout(() => {
              setProgress(0);
              setStatusMessage("");
            }, 2000);
          }
        } catch {
          // Polling error — keep trying
        }
      }, 800);
    } catch {
      toast.error("Failed to start scrape");
      setLoading(false);
      setProgress(0);
      setStatusMessage("");
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto space-y-2">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="Job title or keywords..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location"
          className="sm:w-44 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
        <button
          type="submit"
          disabled={loading || !keywords.trim()}
          className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium text-sm transition-colors"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Search
        </button>
      </form>

      {/* Progress bar */}
      {(loading || progress > 0) && (
        <div className="space-y-1.5">
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          {statusMessage && (
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              {statusMessage}
            </p>
          )}
        </div>
      )}

      {/* Filters toggle */}
      <button
        type="button"
        onClick={() => setShowFilters(!showFilters)}
        className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors mx-auto"
      >
        <ChevronDown className={`w-3 h-3 transition-transform ${showFilters ? "rotate-180" : ""}`} />
        Filters
      </button>

      {/* Filter options */}
      {showFilters && (
        <div className="flex flex-col sm:flex-row gap-3 p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
          <div className="flex-1">
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Time posted</label>
            <select
              value={maxDays}
              onChange={(e) => setMaxDays(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {TIME_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Experience level</label>
            <select
              value={experience}
              onChange={(e) => setExperience(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {EXPERIENCE_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
