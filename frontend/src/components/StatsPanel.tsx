"use client";

import { useState, useEffect } from "react";
import { Loader2, Brain, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { Stats, ModelStatus } from "@/lib/types";
import { getStats, getModelStatus, retrainModel } from "@/lib/api";

export default function StatsPanel() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [s, m] = await Promise.all([getStats(), getModelStatus()]);
        setStats(s);
        setModel(m);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleRetrain() {
    setRetraining(true);
    try {
      const result = await retrainModel();
      setModel(result);
      toast.success(`Model retrained! Accuracy: ${Math.round((result.accuracy || 0) * 100)}%`);
      // Refresh stats
      const s = await getStats();
      setStats(s);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to retrain";
      toast.error(message);
    } finally {
      setRetraining(false);
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
    <div className="space-y-6">
      {/* Swipe stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total Jobs" value={stats?.total_jobs ?? 0} />
        <StatCard label="Total Swipes" value={stats?.total_swipes ?? 0} />
        <StatCard label="Interested" value={stats?.right_swipes ?? 0} color="green" />
        <StatCard label="Passed" value={stats?.left_swipes ?? 0} color="red" />
      </div>

      {/* Model info */}
      <div className="p-5 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Recommendation Model</h3>
          </div>
          <button
            onClick={handleRetrain}
            disabled={retraining}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-purple-50 hover:bg-purple-100 dark:bg-purple-900/30 dark:hover:bg-purple-900/50 text-purple-600 dark:text-purple-400 font-medium transition-colors disabled:opacity-50"
          >
            {retraining ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            Retrain
          </button>
        </div>

        {model?.trained_at ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">Accuracy</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {Math.round((model.accuracy || 0) * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">Precision</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {Math.round((model.precision_right || 0) * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">Recall</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {Math.round((model.recall_right || 0) * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">Trained on</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {model.num_samples} swipes
              </span>
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>Model not yet trained.</p>
            <p className="mt-1">
              Swipe on at least 20 jobs to enable smart ranking.
              {stats && stats.swipes_until_retrain > 0 && (
                <span className="font-medium text-purple-600 dark:text-purple-400">
                  {" "}{stats.swipes_until_retrain} more swipes needed.
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Progress to next retrain */}
      {stats && stats.swipes_until_retrain > 0 && model?.trained_at && (
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium text-gray-900 dark:text-white">
              {stats.swipes_until_retrain}
            </span>{" "}
            swipes until next auto-retrain
          </p>
          <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all"
              style={{ width: `${((20 - stats.swipes_until_retrain) / 20) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: "green" | "red";
}) {
  const colorClasses = {
    green: "text-green-600 dark:text-green-400",
    red: "text-red-600 dark:text-red-400",
  };

  return (
    <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
      <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color ? colorClasses[color] : "text-gray-900 dark:text-white"}`}>
        {value}
      </p>
    </div>
  );
}
