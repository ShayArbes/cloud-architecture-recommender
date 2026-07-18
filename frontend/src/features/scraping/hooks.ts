import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ScrapeJobResponse } from '../../api/types';
import { getScrapeJob, listScrapeJobs, triggerScrape } from './api';

const ACTIVE_POLL_INTERVAL_MS = 1500;

/** Trigger a scrape; on success the caller polls the returned job id. */
export function useTriggerScrape() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerScrape,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['scrape-jobs'] });
    },
  });
}

/** Poll one job while it is pending/running; stops polling once terminal. */
export function useScrapeJob(jobId: string | undefined) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ['scrape-job', jobId],
    queryFn: () => getScrapeJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') {
        // Terminal: refresh the inventory and history once, then stop polling.
        void queryClient.invalidateQueries({ queryKey: ['architectures'] });
        void queryClient.invalidateQueries({ queryKey: ['scrape-jobs'] });
        return false;
      }
      return ACTIVE_POLL_INTERVAL_MS;
    },
  });
}

/** Whether any job in a list is still active (used to disable the trigger). */
export function hasActiveJob(jobs: ScrapeJobResponse[]): boolean {
  return jobs.some((job) => job.status === 'pending' || job.status === 'running');
}

/** Recent scrape-job history. */
export function useScrapeJobs() {
  return useQuery({
    queryKey: ['scrape-jobs'],
    queryFn: listScrapeJobs,
  });
}
