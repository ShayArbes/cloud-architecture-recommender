import { useQuery } from '@tanstack/react-query';

import { getArchitecture, listArchitectures, type ListArchitecturesParams } from './api';

/** Paginated architecture list; keeps the previous page visible while fetching the next. */
export function useArchitectures(params: ListArchitecturesParams) {
  return useQuery({
    queryKey: ['architectures', params],
    queryFn: () => listArchitectures(params),
    placeholderData: (previous) => previous,
  });
}

/** Full detail for one architecture; disabled until a slug is available. */
export function useArchitecture(slug: string | undefined) {
  return useQuery({
    queryKey: ['architecture', slug],
    queryFn: () => getArchitecture(slug as string),
    enabled: Boolean(slug),
  });
}
