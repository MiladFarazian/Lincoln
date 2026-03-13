"use client";

import SavedJobs from "@/components/SavedJobs";

export default function SavedPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Saved Jobs</h1>
      <SavedJobs />
    </div>
  );
}
