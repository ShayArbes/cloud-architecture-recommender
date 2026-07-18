import { apiRequest } from '../../api/client';
import type { RecommendationRequest, RecommendationResponse } from '../../api/types';

export async function getRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  return apiRequest<RecommendationResponse>('/recommendations', {
    method: 'POST',
    body: request,
  });
}
