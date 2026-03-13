import axios from "axios";
import { Job, SwipeDirection, SwipeResult, ModelStatus, Stats, ScrapeResult } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "https://lincoln-production.up.railway.app"
    : "http://localhost:8000");

const api = axios.create({
  baseURL: API_URL,
});

export async function fetchNextJobs(limit: number = 10): Promise<Job[]> {
  const { data } = await api.get<Job[]>("/api/jobs/next", { params: { limit } });
  return data;
}

export async function recordSwipe(jobId: number, direction: SwipeDirection): Promise<SwipeResult> {
  const { data } = await api.post<SwipeResult>("/api/swipe", {
    job_id: jobId,
    direction,
  });
  return data;
}

export async function undoSwipe(swipeId: number): Promise<void> {
  await api.delete(`/api/swipe/${swipeId}`);
}

export async function fetchSavedJobs(page: number = 1): Promise<Job[]> {
  const { data } = await api.get<Job[]>("/api/saved", { params: { page } });
  return data;
}

export async function triggerScrape(keywords: string, location?: string): Promise<ScrapeResult> {
  const { data } = await api.post<ScrapeResult>("/api/scrape", {
    keywords,
    location: location || "",
  });
  return data;
}

export async function getModelStatus(): Promise<ModelStatus> {
  const { data } = await api.get<ModelStatus>("/api/model/status");
  return data;
}

export async function retrainModel(): Promise<ModelStatus> {
  const { data } = await api.post<ModelStatus>("/api/model/retrain");
  return data;
}

export async function getStats(): Promise<Stats> {
  const { data } = await api.get<Stats>("/api/stats");
  return data;
}
