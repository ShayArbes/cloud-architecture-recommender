import { useState } from 'react';
import { Link } from 'react-router-dom';

import type { RecommendationRequest, RecommendationResponse } from '../../api/types';
import { ErrorState } from '../../components/QueryStates';
import {
  AVAILABILITIES,
  COST_PROFILES,
  DATA_INTENSITIES,
  LATENCY_SENSITIVITIES,
  OPS_MODELS,
  PROCESSING_STYLES,
  SCALES,
  TRAFFIC_PATTERNS,
  USE_CASES,
  humanize,
} from '../../constants/enums';
import { useRecommendations } from './hooks';
import { SelectField } from './SelectField';

type FormState = Partial<RecommendationRequest>;

const REQUIRED_FIELDS: (keyof RecommendationRequest)[] = [
  'use_case',
  'scale',
  'traffic_pattern',
  'latency_sensitivity',
  'processing_style',
  'data_intensity',
  'availability_requirement',
  'ops_preference',
  'budget_sensitivity',
];

function isComplete(form: FormState): form is RecommendationRequest {
  return REQUIRED_FIELDS.every((field) => form[field] !== undefined);
}

export function RecommendationsPage() {
  const [form, setForm] = useState<FormState>({});
  const [showValidation, setShowValidation] = useState(false);
  const recommendations = useRecommendations();

  function set<K extends keyof RecommendationRequest>(
    field: K,
    value: RecommendationRequest[K],
  ): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(): void {
    if (!isComplete(form)) {
      setShowValidation(true);
      return;
    }
    setShowValidation(false);
    recommendations.mutate(form);
  }

  return (
    <section>
      <h2>Recommendations</h2>
      <p>Describe your workload across all nine dimensions to get ranked architecture matches.</p>

      <form
        className="reco-form"
        onSubmit={(event) => {
          event.preventDefault();
          handleSubmit();
        }}
        noValidate
      >
        <div className="form-grid">
          <SelectField
            label="Use case"
            value={form.use_case ?? ''}
            options={USE_CASES}
            onChange={(value) => {
              set('use_case', value);
            }}
          />
          <SelectField
            label="Scale"
            value={form.scale ?? ''}
            options={SCALES}
            onChange={(value) => {
              set('scale', value);
            }}
          />
          <SelectField
            label="Traffic pattern"
            value={form.traffic_pattern ?? ''}
            options={TRAFFIC_PATTERNS}
            onChange={(value) => {
              set('traffic_pattern', value);
            }}
          />
          <SelectField
            label="Latency sensitivity"
            value={form.latency_sensitivity ?? ''}
            options={LATENCY_SENSITIVITIES}
            onChange={(value) => {
              set('latency_sensitivity', value);
            }}
          />
          <SelectField
            label="Processing style"
            value={form.processing_style ?? ''}
            options={PROCESSING_STYLES}
            onChange={(value) => {
              set('processing_style', value);
            }}
          />
          <SelectField
            label="Data intensity"
            value={form.data_intensity ?? ''}
            options={DATA_INTENSITIES}
            onChange={(value) => {
              set('data_intensity', value);
            }}
          />
          <SelectField
            label="Availability requirement"
            value={form.availability_requirement ?? ''}
            options={AVAILABILITIES}
            onChange={(value) => {
              set('availability_requirement', value);
            }}
          />
          <SelectField
            label="Ops preference"
            value={form.ops_preference ?? ''}
            options={OPS_MODELS}
            onChange={(value) => {
              set('ops_preference', value);
            }}
          />
          <SelectField
            label="Budget sensitivity"
            value={form.budget_sensitivity ?? ''}
            options={COST_PROFILES}
            onChange={(value) => {
              set('budget_sensitivity', value);
            }}
          />
        </div>

        {showValidation ? (
          <p className="inline-error">Please choose a value for every dimension.</p>
        ) : null}

        <button type="submit" className="primary" disabled={recommendations.isPending}>
          {recommendations.isPending ? 'Scoring…' : 'Get recommendations'}
        </button>
      </form>

      {recommendations.isError ? (
        <ErrorState
          error={recommendations.error}
          onRetry={
            isComplete(form)
              ? () => {
                  recommendations.mutate(form);
                }
              : undefined
          }
        />
      ) : null}

      {recommendations.isSuccess ? <RecommendationResults data={recommendations.data} /> : null}
    </section>
  );
}

function RecommendationResults({ data }: { data: RecommendationResponse }) {
  if (data.recommendations.length === 0) {
    return (
      <div className="state state--empty" role="status">
        No architectures in the inventory yet — trigger a scrape first.
      </div>
    );
  }
  return (
    <div className="results">
      <p className="results-meta">
        Evaluated {data.total_candidates_evaluated}{' '}
        {data.total_candidates_evaluated === 1 ? 'candidate' : 'candidates'}.
      </p>
      <ol className="card-list">
        {data.recommendations.map((recommendation) => (
          <li key={recommendation.architecture.slug} className="card">
            <div className="card-title-row">
              <Link
                to={`/architectures/${recommendation.architecture.slug}`}
                className="card-title"
              >
                {recommendation.architecture.title}
              </Link>
              <span className="score">{Math.round(recommendation.score * 100)}%</span>
            </div>
            <p>{recommendation.explanation}</p>
            <div className="breakdown">
              {Object.entries(recommendation.match_breakdown).map(([dimension, value]) => (
                <span key={dimension} className="breakdown-item">
                  {humanize(dimension)}: {Math.round(value * 100)}%
                </span>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
