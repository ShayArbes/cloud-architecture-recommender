import { Link, useParams } from 'react-router-dom';

import { ApiError } from '../../api/client';
import type { ArchitectureCharacteristics } from '../../api/types';
import { EmptyState, ErrorState, LoadingState } from '../../components/QueryStates';
import { humanize } from '../../constants/enums';
import { useArchitecture } from './hooks';

/** The 9 characteristic dimensions rendered as labelled rows. */
function CharacteristicsTable({
  characteristics,
}: {
  characteristics: ArchitectureCharacteristics;
}) {
  const rows: [string, string][] = [
    ['Use cases', characteristics.use_cases.map(humanize).join(', ')],
    ['Scale', characteristics.scale.map(humanize).join(', ')],
    ['Traffic patterns', characteristics.traffic_patterns.map(humanize).join(', ')],
    ['Latency sensitivity', humanize(characteristics.latency_sensitivity)],
    ['Processing styles', characteristics.processing_styles.map(humanize).join(', ')],
    ['Data intensity', humanize(characteristics.data_intensity)],
    ['Availability', humanize(characteristics.availability)],
    ['Ops model', humanize(characteristics.ops_model)],
    ['Cost profile', humanize(characteristics.cost_profile)],
  ];
  return (
    <table className="detail-table">
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ArchitectureDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const query = useArchitecture(slug);

  if (query.isPending) {
    return <LoadingState label="Loading architecture…" />;
  }

  if (query.isError) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState>
          That architecture could not be found. <Link to="/architectures">Back to the list</Link>.
        </EmptyState>
      );
    }
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }

  const architecture = query.data;
  return (
    <article className="detail">
      <Link to="/architectures" className="back-link">
        ← All architectures
      </Link>
      <h2>{architecture.title}</h2>
      <p className="detail-description">{architecture.description}</p>
      <p>
        <a href={architecture.source_url} target="_blank" rel="noreferrer">
          View on AWS ↗
        </a>
      </p>

      {architecture.diagram_url ? (
        <img
          className="detail-diagram"
          src={architecture.diagram_url}
          alt={`${architecture.title} architecture diagram`}
        />
      ) : null}

      <h3>Characteristics</h3>
      <CharacteristicsTable characteristics={architecture.characteristics} />

      <h3>AWS services ({architecture.aws_services.length})</h3>
      <ul className="service-list">
        {architecture.aws_services.map((service) => (
          <li key={service.name}>
            <strong>{service.name}</strong>{' '}
            <span className="pill">{humanize(service.category)}</span>
            <p>{service.purpose}</p>
          </li>
        ))}
      </ul>

      {architecture.tags.length > 0 ? (
        <>
          <h3>Tags</h3>
          <div className="pill-row">
            {architecture.tags.map((tag) => (
              <span key={tag} className="pill">
                {tag}
              </span>
            ))}
          </div>
        </>
      ) : null}
    </article>
  );
}
