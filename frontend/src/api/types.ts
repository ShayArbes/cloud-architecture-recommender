/**
 * TypeScript types mirroring the backend API schemas (backend/app/schemas/*).
 * Kept in lockstep with the server DTOs — no `any`, no untyped responses.
 */

import type {
  Availability,
  CostProfile,
  DataIntensity,
  LatencySensitivity,
  OpsModel,
  ProcessingStyle,
  Scale,
  ScrapeJobStatus,
  ServiceCategory,
  TrafficPattern,
  TriggerSource,
  UseCase,
} from '../constants/enums';

export interface ArchitectureSummary {
  slug: string;
  title: string;
  source_url: string;
  description: string;
  use_cases: UseCase[];
  service_count: number;
  tags: string[];
  scraped_at: string;
  parsed_at: string;
}

export interface AwsService {
  name: string;
  category: ServiceCategory;
  purpose: string;
}

export interface ArchitectureCharacteristics {
  use_cases: UseCase[];
  scale: Scale[];
  traffic_patterns: TrafficPattern[];
  latency_sensitivity: LatencySensitivity;
  processing_styles: ProcessingStyle[];
  data_intensity: DataIntensity;
  availability: Availability;
  ops_model: OpsModel;
  cost_profile: CostProfile;
}

export interface ArchitectureDetail {
  slug: string;
  title: string;
  source_url: string;
  description: string;
  use_cases: UseCase[];
  aws_services: AwsService[];
  characteristics: ArchitectureCharacteristics;
  diagram_url: string | null;
  tags: string[];
  parser_version: string;
  scraped_at: string;
  parsed_at: string;
}

export interface PageMeta {
  total: number;
  limit: number;
  offset: number;
}

export interface ArchitectureListResponse {
  items: ArchitectureSummary[];
  page: PageMeta;
}

export interface RecommendationRequest {
  use_case: UseCase;
  scale: Scale;
  traffic_pattern: TrafficPattern;
  latency_sensitivity: LatencySensitivity;
  processing_style: ProcessingStyle;
  data_intensity: DataIntensity;
  availability_requirement: Availability;
  ops_preference: OpsModel;
  budget_sensitivity: CostProfile;
}

export interface Recommendation {
  architecture: ArchitectureSummary;
  score: number;
  explanation: string;
  match_breakdown: Record<string, number>;
}

export interface RecommendationResponse {
  recommendations: Recommendation[];
  total_candidates_evaluated: number;
}

export interface ScrapeJobStats {
  pages_found: number;
  parsed_ok: number;
  failed: number;
}

export interface ScrapeJobError {
  url: string;
  reason: string;
}

export interface TriggerScrapeResponse {
  job_id: string;
  status: ScrapeJobStatus;
}

export interface ScrapeJobResponse {
  job_id: string;
  status: ScrapeJobStatus;
  trigger_source: TriggerSource;
  stats: ScrapeJobStats;
  errors: ScrapeJobError[];
  started_at: string;
  finished_at: string | null;
}

export interface ScrapeJobListResponse {
  items: ScrapeJobResponse[];
}

/** The server's error envelope (backend/app/core/errors.py §3.5). */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
