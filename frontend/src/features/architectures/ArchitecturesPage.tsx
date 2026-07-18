import { useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState, ErrorState, LoadingState } from '../../components/QueryStates';
import { USE_CASES, humanize, type UseCase } from '../../constants/enums';
import { useArchitectures } from './hooks';

const PAGE_SIZE = 20;

export function ArchitecturesPage() {
  const [offset, setOffset] = useState(0);
  const [useCase, setUseCase] = useState<UseCase | ''>('');

  const query = useArchitectures({
    limit: PAGE_SIZE,
    offset,
    useCase: useCase || undefined,
  });

  function handleUseCaseChange(value: string): void {
    setUseCase(value as UseCase | '');
    setOffset(0); // reset to the first page when the filter changes
  }

  return (
    <section>
      <div className="page-heading">
        <h2>Architectures</h2>
        <label className="filter">
          Use case
          <select
            value={useCase}
            onChange={(event) => {
              handleUseCaseChange(event.target.value);
            }}
          >
            <option value="">All</option>
            {USE_CASES.map((value) => (
              <option key={value} value={value}>
                {humanize(value)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {query.isPending ? <LoadingState label="Loading architectures…" /> : null}

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}

      {query.isSuccess && query.data.items.length === 0 ? (
        <EmptyState>
          No architectures yet. Trigger a scrape from the <Link to="/scraping">Scraping</Link> tab
          to build the inventory.
        </EmptyState>
      ) : null}

      {query.isSuccess && query.data.items.length > 0 ? (
        <>
          <ul className="card-list">
            {query.data.items.map((architecture) => (
              <li key={architecture.slug} className="card">
                <Link to={`/architectures/${architecture.slug}`} className="card-title">
                  {architecture.title}
                </Link>
                <p className="card-description">{architecture.description}</p>
                <div className="pill-row">
                  {architecture.use_cases.map((value) => (
                    <span key={value} className="pill">
                      {humanize(value)}
                    </span>
                  ))}
                </div>
                <div className="card-meta">
                  <span>{architecture.service_count} AWS services</span>
                  <span>Scraped {new Date(architecture.scraped_at).toLocaleDateString()}</span>
                </div>
              </li>
            ))}
          </ul>

          <nav className="pagination" aria-label="Pagination">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => {
                setOffset((current) => Math.max(0, current - PAGE_SIZE));
              }}
            >
              Previous
            </button>
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, query.data.page.total)} of{' '}
              {query.data.page.total}
            </span>
            <button
              type="button"
              disabled={offset + PAGE_SIZE >= query.data.page.total}
              onClick={() => {
                setOffset((current) => current + PAGE_SIZE);
              }}
            >
              Next
            </button>
          </nav>
        </>
      ) : null}
    </section>
  );
}
