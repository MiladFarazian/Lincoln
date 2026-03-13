"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Copy, Download, RefreshCw, Loader2, FileWarning } from "lucide-react";
import toast from "react-hot-toast";
import { Job } from "@/lib/types";
import { craftResume } from "@/lib/api";

interface CraftedResumeModalProps {
  job: Job | null;
  onClose: () => void;
}

export default function CraftedResumeModal({ job, onClose }: CraftedResumeModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job) return;
    setContent(null);
    setError(null);
    handleCraft(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.id]);

  async function handleCraft(force: boolean) {
    if (!job) return;
    setLoading(true);
    setError(null);
    try {
      const result = await craftResume(job.id, force);
      setContent(result.crafted_content);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Failed to craft resume";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleCopy() {
    if (!content) return;
    navigator.clipboard.writeText(content);
    toast.success("Copied to clipboard!");
  }

  function handleDownload() {
    if (!content || !job) return;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resume-${job.company?.replace(/\s+/g, "-").toLowerCase() || "tailored"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!job) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="absolute inset-0 bg-black/50" onClick={onClose} />

        <motion.div
          className="relative w-full max-w-2xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
        >
          {/* Header */}
          <div className="p-6 pb-4 border-b border-gray-100 dark:border-gray-700">
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>

            <h2 className="text-lg font-bold text-gray-900 dark:text-white pr-8">
              Tailored Resume
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {job.title} at {job.company || "Unknown"}
            </p>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin mb-3" />
                <p className="text-sm font-medium">Crafting your resume...</p>
                <p className="text-xs mt-1">This may take 10-15 seconds</p>
              </div>
            )}

            {error && !loading && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
                <FileWarning className="w-10 h-10 mb-3 text-amber-500" />
                <p className="text-sm font-medium text-center">{error}</p>
                {error.includes("resume first") && (
                  <a
                    href="/resume"
                    className="mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Go to Resume page to add yours
                  </a>
                )}
              </div>
            )}

            {content && !loading && (
              <pre className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap font-sans">
                {content}
              </pre>
            )}
          </div>

          {/* Actions */}
          {content && !loading && (
            <div className="p-4 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium transition-colors"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
              <button
                onClick={() => handleCraft(true)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium transition-colors ml-auto"
              >
                <RefreshCw className="w-4 h-4" />
                Re-craft
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
