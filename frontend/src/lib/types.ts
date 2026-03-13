export interface Job {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  url: string | null;
  salary: string | null;
  date_posted: string | null;
  score: number | null;
}

export type SwipeDirection = "left" | "right";

export interface SwipeResult {
  id: number;
  job_id: number;
  direction: string;
  timestamp: string;
}

export interface ModelStatus {
  trained_at: string | null;
  num_samples: number | null;
  accuracy: number | null;
  precision_right: number | null;
  recall_right: number | null;
}

export interface Stats {
  total_jobs: number;
  total_swipes: number;
  right_swipes: number;
  left_swipes: number;
  model_accuracy: number | null;
  swipes_until_retrain: number;
}

export interface ScrapeResult {
  search_id: number;
  jobs_found: number;
}
