import { apiRequest } from '../../api/client';
import type { ArchitectureDetail, ArchitectureListResponse } from '../../api/types';
import type { UseCase } from '../../constants/enums';

export interface ListArchitecturesParams {
  limit: number;
  offset: number;
  useCase?: UseCase;
  tag?: string;
}

export async function listArchitectures(
  params: ListArchitecturesParams,
): Promise<ArchitectureListResponse> {
  const query = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  });
  if (params.useCase) {
    query.set('use_case', params.useCase);
  }
  if (params.tag) {
    query.set('tag', params.tag);
  }
  return apiRequest<ArchitectureListResponse>(`/architectures?${query.toString()}`);
}

export async function getArchitecture(slug: string): Promise<ArchitectureDetail> {
  return apiRequest<ArchitectureDetail>(`/architectures/${encodeURIComponent(slug)}`);
}
