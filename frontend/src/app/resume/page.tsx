"use client";

import { useState, useEffect } from "react";
import { Loader2, Save, Check } from "lucide-react";
import toast from "react-hot-toast";
import { getResume, saveResume } from "@/lib/api";

export default function ResumePage() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function load() {
      const resume = await getResume();
      if (resume) setContent(resume.content);
      setLoading(false);
    }
    load();
  }, []);

  async function handleSave() {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await saveResume(content);
      setSaved(true);
      toast.success("Resume saved!");
      setTimeout(() => setSaved(false), 2000);
    } catch {
      toast.error("Failed to save resume");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Resume</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Paste your resume below. This will be used to craft tailored versions for each job.
        </p>
      </div>

      <textarea
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          setSaved(false);
        }}
        placeholder="Paste your resume text here..."
        rows={20}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm leading-relaxed resize-y"
      />

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving || !content.trim()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium text-sm transition-colors"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saving ? "Saving..." : saved ? "Saved" : "Save Resume"}
        </button>
        <span className="text-xs text-gray-400">
          {content.length > 0 ? `${content.length.toLocaleString()} characters` : ""}
        </span>
      </div>
    </div>
  );
}
