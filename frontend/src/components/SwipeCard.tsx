"use client";

import { motion, useMotionValue, useTransform, PanInfo } from "framer-motion";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { Job, SwipeDirection } from "@/lib/types";

interface SwipeCardProps {
  job: Job;
  onSwipe: (direction: SwipeDirection) => void;
  isTop: boolean;
  stackIndex: number;
  onExpand: () => void;
}

const SWIPE_THRESHOLD = 150;

function formatDate(dateStr: string): string {
  // Handle epoch timestamps
  const num = Number(dateStr);
  if (!isNaN(num) && num > 1000000000) {
    const d = new Date(num * 1000);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  // Handle ISO and other date strings
  const d = new Date(dateStr);
  if (!isNaN(d.getTime())) {
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  return dateStr;
}

export default function SwipeCard({ job, onSwipe, isTop, stackIndex, onExpand }: SwipeCardProps) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-300, 0, 300], [-15, 0, 15]);
  const rightOpacity = useTransform(x, [0, 100, 200], [0, 0.5, 1]);
  const leftOpacity = useTransform(x, [-200, -100, 0], [1, 0.5, 0]);

  const scale = 1 - stackIndex * 0.05;
  const yOffset = stackIndex * 8;

  function handleDragEnd(_: unknown, info: PanInfo) {
    if (info.offset.x > SWIPE_THRESHOLD) {
      onSwipe("right");
    } else if (info.offset.x < -SWIPE_THRESHOLD) {
      onSwipe("left");
    }
  }

  const truncatedDescription = job.description
    ? job.description.slice(0, 200) + (job.description.length > 200 ? "..." : "")
    : "No description available";

  return (
    <motion.div
      className="absolute w-full max-w-sm cursor-grab active:cursor-grabbing"
      style={{
        x: isTop ? x : 0,
        rotate: isTop ? rotate : 0,
        scale,
        y: yOffset,
        zIndex: 10 - stackIndex,
      }}
      drag={isTop ? "x" : false}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.9}
      onDragEnd={isTop ? handleDragEnd : undefined}
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale, opacity: 1, y: yOffset }}
      exit={{
        x: 500,
        opacity: 0,
        transition: { duration: 0.3 },
      }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
    >
      <div
        className="relative overflow-hidden rounded-2xl bg-white shadow-xl border border-gray-100 dark:bg-gray-800 dark:border-gray-700"
        onClick={isTop ? onExpand : undefined}
      >
        {/* Swipe indicators */}
        {isTop && (
          <>
            <motion.div
              className="absolute inset-0 bg-green-500/20 rounded-2xl flex items-center justify-center z-10 pointer-events-none"
              style={{ opacity: rightOpacity }}
            >
              <ThumbsUp className="w-16 h-16 text-green-500" />
            </motion.div>
            <motion.div
              className="absolute inset-0 bg-red-500/20 rounded-2xl flex items-center justify-center z-10 pointer-events-none"
              style={{ opacity: leftOpacity }}
            >
              <ThumbsDown className="w-16 h-16 text-red-500" />
            </motion.div>
          </>
        )}

        {/* Card content */}
        <div className="p-6">
          {/* Score badge */}
          {job.score !== null && (
            <div className="absolute top-4 right-4 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs font-medium px-2.5 py-1 rounded-full">
              {Math.round(job.score * 100)}% match
            </div>
          )}

          <h2 className="text-xl font-bold text-gray-900 dark:text-white pr-20 leading-tight">
            {job.title}
          </h2>
          <p className="text-base font-medium text-blue-600 dark:text-blue-400 mt-1">
            {job.company || "Unknown Company"}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {job.location || "Location not specified"}
          </p>

          {job.salary && (
            <p className="text-sm font-semibold text-green-600 dark:text-green-400 mt-2">
              {job.salary}
            </p>
          )}

          {job.date_posted && (
            <p className="text-xs text-gray-400 mt-1">Posted: {formatDate(job.date_posted)}</p>
          )}

          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
              {truncatedDescription}
            </p>
          </div>

          <p className="text-xs text-gray-400 mt-3 text-center">
            Tap to view full details
          </p>
        </div>
      </div>
    </motion.div>
  );
}
