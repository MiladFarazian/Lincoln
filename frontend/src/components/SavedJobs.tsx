"use client";

import { useState, useEffect } from "react";
import { Loader2, ExternalLink, BookmarkCheck, FileText } from "lucide-react";
import { Job } from "@/lib/types";
import { fetchSavedJobs } from "@/lib/api";
import CraftedResumeModal from "./CraftedResumeModal";

export default function SavedJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [craftingJob, setCraftingJob] = useState<Job | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await fetchSavedJobs(page);
        if (data.length < 20) setHasMore(false);
        setJobs((prev) => (page === 1 ? data : [...prev, ...data]));
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [page]);

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <BookmarkCheck className="w-12 h-12 mb-3" />
        <p className="text-lg font-medium">No saved jobs yet</p>
        <p className="text-sm mt-1">Swipe right on jobs you&apos;re interested in</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {jobs.map((job) => (
          <div
            key={job.id}
            className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                  {job.title}
                </h3>
                <p className="text-sm text-blue-600 dark:text-blue-400">
                  {job.company || "Unknown Company"}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {job.location || "Location not specified"}
                </p>
                {job.salary && (
                  <p className="text-xs font-medium text-green-600 dark:text-green-400 mt-1">
                    {job.salary}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 ml-3">
                {job.score !== null && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                    {Math.round(job.score * 100)}%
                  </span>
                )}
                <button
                  onClick={() => setCraftingJob(job)}
                  className="p-2 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-900/30 text-purple-500 transition-colors"
                  title="Craft tailored resume"
                >
                  <FileText className="w-4 h-4" />
                </button>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}

        {hasMore && (
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={loading}
            className="w-full py-3 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-colors font-medium"
          >
            {loading ? "Loading..." : "Load more"}
          </button>
        )}
      </div>

      <CraftedResumeModal job={craftingJob} onClose={() => setCraftingJob(null)} />
    </>
  );
}
