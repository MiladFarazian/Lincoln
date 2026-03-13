"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, ThumbsUp, ThumbsDown } from "lucide-react";
import { Job, SwipeDirection } from "@/lib/types";

interface JobDetailProps {
  job: Job | null;
  onClose: () => void;
  onSwipe: (direction: SwipeDirection) => void;
}

export default function JobDetail({ job, onClose, onSwipe }: JobDetailProps) {
  if (!job) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/50" onClick={onClose} />

        {/* Modal */}
        <motion.div
          className="relative w-full max-w-lg max-h-[85vh] bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col"
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

            <h2 className="text-2xl font-bold text-gray-900 dark:text-white pr-8">
              {job.title}
            </h2>
            <p className="text-lg font-medium text-blue-600 dark:text-blue-400 mt-1">
              {job.company || "Unknown Company"}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {job.location || "Location not specified"}
            </p>

            <div className="flex items-center gap-3 mt-3">
              {job.salary && (
                <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                  {job.salary}
                </span>
              )}
              {job.score !== null && (
                <span className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs font-medium px-2.5 py-1 rounded-full">
                  {Math.round(job.score * 100)}% match
                </span>
              )}
              {job.date_posted && (
                <span className="text-xs text-gray-400">Posted: {job.date_posted}</span>
              )}
            </div>
          </div>

          {/* Description */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">
              {job.description || "No description available."}
            </div>
          </div>

          {/* Actions */}
          <div className="p-4 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3">
            <button
              onClick={() => onSwipe("left")}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-red-50 hover:bg-red-100 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 font-medium transition-colors"
            >
              <ThumbsDown className="w-5 h-5" />
              Pass
            </button>
            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center p-3 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 transition-colors"
              >
                <ExternalLink className="w-5 h-5" />
              </a>
            )}
            <button
              onClick={() => onSwipe("right")}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-green-50 hover:bg-green-100 dark:bg-green-900/30 dark:hover:bg-green-900/50 text-green-600 dark:text-green-400 font-medium transition-colors"
            >
              <ThumbsUp className="w-5 h-5" />
              Interested
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
