import { apiRequest } from '../../api/client';
import type {
  ScrapeJobListResponse,
  ScrapeJobResponse,
  TriggerScrapeResponse,
} from '../../api/types';

export async function triggerScrape(): Promise<TriggerScrapeResponse> {
  return apiRequest<TriggerScrapeResponse>('/scrape', { method: 'POST' });
}

export async function getScrapeJob(jobId: string): Promise<ScrapeJobResponse> {
  return apiRequest<ScrapeJobResponse>(`/scrape/jobs/${encodeURIComponent(jobId)}`);
}

export async function listScrapeJobs(): Promise<ScrapeJobListResponse> {
  return apiRequest<ScrapeJobListResponse>('/scrape/jobs');
}
