import { useState } from 'react';

import { ApiError } from '../../api/client';
import type { ScrapeJobResponse } from '../../api/types';
import { EmptyState, ErrorState, LoadingState } from '../../components/QueryStates';
import { hasActiveJob, useScrapeJob, useScrapeJobs, useTriggerScrape } from './hooks';

function StatusBadge({ status }: { status: ScrapeJobResponse['status'] }) {
  return <span className={`status status--${status}`}>{status}</span>;
}

function JobStats({ job }: { job: ScrapeJobResponse }) {
  return (
    <div className="card-meta">
      <span>{job.stats.pages_found} found</span>
      <span>{job.stats.parsed_ok} parsed</span>
      <span>{job.stats.failed} failed</span>
    </div>
  );
}

export function ScrapingPage() {
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);

  const trigger = useTriggerScrape();
  const activeJob = useScrapeJob(activeJobId);
  const history = useScrapeJobs();

  // The trigger is blocked while the just-started job or any historical job is active.
  const jobRunning =
    activeJob.data?.status === 'pending' ||
    activeJob.data?.status === 'running' ||
    (history.data ? hasActiveJob(history.data.items) : false);

  function handleTrigger(): void {
    trigger.mutate(undefined, {
      onSuccess: (response) => {
        setActiveJobId(response.job_id);
      },
    });
  }

  const triggerError =
    trigger.error instanceof ApiError && trigger.error.status === 409
      ? 'A scrape job is already running. Wait for it to finish.'
      : trigger.error
        ? 'Could not start the scrape job.'
        : null;

  return (
    <section>
      <h2>Scraping</h2>
      <p>
        Trigger a scrape to (re)build the architecture inventory from the AWS Architecture Center.
      </p>

      <button
        type="button"
        className="primary"
        onClick={handleTrigger}
        disabled={trigger.isPending || jobRunning}
      >
        {trigger.isPending ? 'Starting…' : jobRunning ? 'Scrape in progress…' : 'Start scrape'}
      </button>
      {triggerError ? <p className="inline-error">{triggerError}</p> : null}

      {activeJobId ? (
        <div className="active-job">
          <h3>Current job</h3>
          {activeJob.isPending ? <LoadingState label="Fetching job status…" /> : null}
          {activeJob.isError ? (
            <ErrorState error={activeJob.error} onRetry={() => void activeJob.refetch()} />
          ) : null}
          {activeJob.data ? (
            <div className="card">
              <div className="card-title-row">
                <span className="mono">{activeJob.data.job_id}</span>
                <StatusBadge status={activeJob.data.status} />
              </div>
              <JobStats job={activeJob.data} />
              {activeJob.data.errors.length > 0 ? (
                <details>
                  <summary>{activeJob.data.errors.length} page errors</summary>
                  <ul>
                    {activeJob.data.errors.map((error) => (
                      <li key={error.url}>
                        <span className="mono">{error.url}</span>: {error.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <h3>Recent jobs</h3>
      {history.isPending ? <LoadingState label="Loading job history…" /> : null}
      {history.isError ? (
        <ErrorState error={history.error} onRetry={() => void history.refetch()} />
      ) : null}
      {history.isSuccess && history.data.items.length === 0 ? (
        <EmptyState>No scrape jobs have run yet.</EmptyState>
      ) : null}
      {history.isSuccess && history.data.items.length > 0 ? (
        <ul className="card-list">
          {history.data.items.map((job) => (
            <li key={job.job_id} className="card">
              <div className="card-title-row">
                <span className="mono">{job.job_id}</span>
                <StatusBadge status={job.status} />
              </div>
              <JobStats job={job} />
              <div className="card-meta">
                <span>Started {new Date(job.started_at).toLocaleString()}</span>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
