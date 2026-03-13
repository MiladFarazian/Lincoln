"use client";

import { useState, useEffect, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import { Loader2, SearchX } from "lucide-react";
import toast from "react-hot-toast";
import SwipeCard from "./SwipeCard";
import JobDetail from "./JobDetail";
import CraftedResumeModal from "./CraftedResumeModal";
import { Job, SwipeDirection, SwipeResult } from "@/lib/types";
import { fetchNextJobs, recordSwipe, undoSwipe } from "@/lib/api";

export default function CardStack() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedJob, setExpandedJob] = useState<Job | null>(null);
  const [lastSwipe, setLastSwipe] = useState<{ job: Job; result: SwipeResult } | null>(null);
  const [craftingJob, setCraftingJob] = useState<Job | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchNextJobs(10);
      setJobs((prev) => {
        const existingIds = new Set(prev.map((j) => j.id));
        const newJobs = data.filter((j) => !existingIds.has(j.id));
        return [...prev, ...newJobs];
      });
    } catch {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Prefetch when running low
  useEffect(() => {
    if (jobs.length <= 3 && !loading) {
      loadJobs();
    }
  }, [jobs.length, loading, loadJobs]);

  const handleSwipe = useCallback(
    async (direction: SwipeDirection) => {
      const job = jobs[0];
      if (!job) return;

      setJobs((prev) => prev.slice(1));
      setExpandedJob(null);

      try {
        const result = await recordSwipe(job.id, direction);
        setLastSwipe({ job, result });
        if (direction === "right") {
          toast.success("Saved to interested!", { icon: "👍" });
        }
      } catch {
        toast.error("Failed to record swipe");
        // Put the job back
        setJobs((prev) => [job, ...prev]);
      }
    },
    [jobs]
  );

  const handleUndo = useCallback(async () => {
    if (!lastSwipe) return;
    try {
      await undoSwipe(lastSwipe.result.id);
      setJobs((prev) => [lastSwipe.job, ...prev]);
      setLastSwipe(null);
      toast.success("Undo successful");
    } catch {
      toast.error("Failed to undo");
    }
  }, [lastSwipe]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't intercept keys when typing in an input
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (expandedJob) {
        if (e.key === "Escape") setExpandedJob(null);
        if (e.key === "ArrowLeft" || e.key === "h") handleSwipe("left");
        if (e.key === "ArrowRight" || e.key === "l") handleSwipe("right");
        return;
      }
      if (e.key === "ArrowLeft" || e.key === "h") handleSwipe("left");
      if (e.key === "ArrowRight" || e.key === "l") handleSwipe("right");
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (jobs[0]) setExpandedJob(jobs[0]);
      }
      if (e.key === "z" && (e.metaKey || e.ctrlKey)) handleUndo();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [expandedJob, handleSwipe, handleUndo, jobs]);

  if (loading && jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-gray-500">
        <Loader2 className="w-8 h-8 animate-spin mb-3" />
        <p>Loading jobs...</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-gray-500 dark:text-gray-400">
        <SearchX className="w-12 h-12 mb-3" />
        <p className="text-lg font-medium">No more jobs to review</p>
        <p className="text-sm mt-1">Try searching for new jobs above</p>
      </div>
    );
  }

  return (
    <>
      <div className="relative h-[480px] w-full max-w-sm mx-auto flex items-center justify-center">
        <AnimatePresence mode="popLayout">
          {jobs.slice(0, 3).map((job, index) => (
            <SwipeCard
              key={job.id}
              job={job}
              isTop={index === 0}
              stackIndex={index}
              onSwipe={handleSwipe}
              onExpand={() => setExpandedJob(job)}
            />
          ))}
        </AnimatePresence>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-4 mt-4">
        {lastSwipe && (
          <button
            onClick={handleUndo}
            className="px-4 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 transition-colors"
          >
            Undo (⌘Z)
          </button>
        )}
        <button
          onClick={() => handleSwipe("left")}
          className="w-14 h-14 rounded-full bg-red-50 hover:bg-red-100 dark:bg-red-900/30 dark:hover:bg-red-900/50 flex items-center justify-center text-red-500 transition-colors shadow-sm"
        >
          ←
        </button>
        <button
          onClick={() => jobs[0] && setExpandedJob(jobs[0])}
          className="w-10 h-10 rounded-full bg-gray-50 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 flex items-center justify-center text-gray-500 transition-colors shadow-sm text-xs"
        >
          Info
        </button>
        <button
          onClick={() => handleSwipe("right")}
          className="w-14 h-14 rounded-full bg-green-50 hover:bg-green-100 dark:bg-green-900/30 dark:hover:bg-green-900/50 flex items-center justify-center text-green-500 transition-colors shadow-sm"
        >
          →
        </button>
      </div>

      {/* Keyboard hint */}
      <p className="text-center text-xs text-gray-400 mt-3">
        ← → to swipe &middot; Space to expand &middot; ⌘Z to undo
      </p>

      {/* Job detail modal */}
      <AnimatePresence>
        {expandedJob && (
          <JobDetail
            job={expandedJob}
            onClose={() => setExpandedJob(null)}
            onSwipe={handleSwipe}
            onCraftResume={(job) => {
              setExpandedJob(null);
              setCraftingJob(job);
            }}
          />
        )}
      </AnimatePresence>

      <CraftedResumeModal job={craftingJob} onClose={() => setCraftingJob(null)} />
    </>
  );
}
