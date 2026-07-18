import { useMutation } from '@tanstack/react-query';

import { getRecommendations } from './api';

/** Submit the requirements form and receive ranked recommendations. */
export function useRecommendations() {
  return useMutation({
    mutationFn: getRecommendations,
  });
}
