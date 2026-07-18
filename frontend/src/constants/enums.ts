/**
 * The 9 recommendation dimensions plus supporting enums, mirroring the backend
 * StrEnums (backend/app/models/enums.py) exactly. Defined once and imported
 * everywhere — form options are derived from these arrays, never hardcoded.
 */

export const USE_CASES = [
  'web_application',
  'public_api',
  'ecommerce',
  'real_time_analytics',
  'batch_processing',
  'event_processing',
  'media_delivery',
  'internal_tool',
  'iot_ingestion',
  'ml_inference',
] as const;
export type UseCase = (typeof USE_CASES)[number];

export const SCALES = ['small', 'medium', 'large'] as const;
export type Scale = (typeof SCALES)[number];

export const TRAFFIC_PATTERNS = [
  'steady',
  'bursty',
  'spiky',
  'scheduled',
  'unpredictable',
] as const;
export type TrafficPattern = (typeof TRAFFIC_PATTERNS)[number];

export const LATENCY_SENSITIVITIES = ['low', 'medium', 'high'] as const;
export type LatencySensitivity = (typeof LATENCY_SENSITIVITIES)[number];

export const PROCESSING_STYLES = [
  'request_response',
  'event_driven',
  'batch',
  'streaming',
] as const;
export type ProcessingStyle = (typeof PROCESSING_STYLES)[number];

export const DATA_INTENSITIES = ['low', 'medium', 'high'] as const;
export type DataIntensity = (typeof DATA_INTENSITIES)[number];

export const AVAILABILITIES = ['standard', 'high', 'critical'] as const;
export type Availability = (typeof AVAILABILITIES)[number];

export const OPS_MODELS = ['managed_services', 'balanced', 'self_managed_ok'] as const;
export type OpsModel = (typeof OPS_MODELS)[number];

export const COST_PROFILES = ['low', 'medium', 'high'] as const;
export type CostProfile = (typeof COST_PROFILES)[number];

export type ServiceCategory =
  | 'compute'
  | 'storage'
  | 'database'
  | 'networking'
  | 'analytics'
  | 'integration'
  | 'ml'
  | 'security'
  | 'other';

export type ScrapeJobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type TriggerSource = 'api' | 'seed' | 'manual';

/** Turn an enum value (`real_time_analytics`) into a display label (`Real Time Analytics`). */
export function humanize(value: string): string {
  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
