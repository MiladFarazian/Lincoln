"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { triggerScrape } from "@/lib/api";

interface SearchBarProps {
  onScrapeComplete?: () => void;
}

export default function SearchBar({ onScrapeComplete }: SearchBarProps) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keywords.trim()) return;

    setLoading(true);
    try {
      const result = await triggerScrape(keywords, location);
      toast.success(`Scrape started! Search ID: ${result.search_id}`, {
        duration: 3000,
      });
      onScrapeComplete?.();
    } catch {
      toast.error("Failed to start scrape");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 w-full max-w-xl mx-auto">
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
        placeholder="Location (optional)"
        className="sm:w-48 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
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
        Scrape
      </button>
    </form>
  );
}
