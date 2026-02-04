/**
 * URL state management utilities
 */

import { useSearchParams } from 'react-router-dom';
import { useCallback } from 'react';
import { AnomalyFilters } from '@mane/shared/types/api';
import { AnomalyType, ValidationStatus } from '@mane/shared/types/enums';

/**
 * Serialize filters to URL search params
 */
export function filtersToSearchParams(filters: AnomalyFilters): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.symbols?.length) {
    params.set('symbols', filters.symbols.join(','));
  }
  if (filters.types?.length) {
    params.set('types', filters.types.join(','));
  }
  if (filters.validationStatus?.length) {
    params.set('validation', filters.validationStatus.join(','));
  }
  if (filters.startDate) {
    params.set('startDate', filters.startDate);
  }
  if (filters.endDate) {
    params.set('endDate', filters.endDate);
  }
  if (filters.page && filters.page > 1) {
    params.set('page', filters.page.toString());
  }
  if (filters.limit && filters.limit !== 20) {
    params.set('limit', filters.limit.toString());
  }

  return params;
}

/**
 * Parse URL search params to filters
 */
export function searchParamsToFilters(params: URLSearchParams): AnomalyFilters {
  const filters: AnomalyFilters = {};

  const symbols = params.get('symbols');
  if (symbols) {
    filters.symbols = symbols.split(',');
  }

  const types = params.get('types');
  if (types) {
    filters.types = types.split(',').filter((t) =>
      Object.values(AnomalyType).includes(t as AnomalyType)
    ) as AnomalyType[];
  }

  const validation = params.get('validation');
  if (validation) {
    filters.validationStatus = validation.split(',').filter((v) =>
      Object.values(ValidationStatus).includes(v as ValidationStatus)
    ) as ValidationStatus[];
  }

  const startDate = params.get('startDate');
  if (startDate) {
    filters.startDate = startDate;
  }

  const endDate = params.get('endDate');
  if (endDate) {
    filters.endDate = endDate;
  }

  const page = params.get('page');
  if (page) {
    const pageNum = parseInt(page, 10);
    if (!isNaN(pageNum) && pageNum > 0) {
      filters.page = pageNum;
    }
  }

  const limit = params.get('limit');
  if (limit) {
    const limitNum = parseInt(limit, 10);
    if (!isNaN(limitNum) && limitNum > 0) {
      filters.limit = limitNum;
    }
  }

  return filters;
}

/**
 * Hook to manage filters in URL state
 */
export function useFilterState(defaultLimit: number = 20) {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse current filters from URL
  const filters = searchParamsToFilters(searchParams);

  // Set default limit if not present
  if (!filters.limit) {
    filters.limit = defaultLimit;
  }

  // Set default page if not present
  if (!filters.page) {
    filters.page = 1;
  }

  // Update filters (and URL)
  const setFilters = useCallback(
    (newFilters: AnomalyFilters) => {
      const params = filtersToSearchParams(newFilters);
      setSearchParams(params, { replace: true });
    },
    [setSearchParams]
  );

  // Update a single filter field
  const updateFilter = useCallback(
    (key: keyof AnomalyFilters, value: any) => {
      const updated = { ...filters, [key]: value };
      // Reset to page 1 when filters change (except when updating page itself)
      if (key !== 'page') {
        updated.page = 1;
      }
      setFilters(updated);
    },
    [filters, setFilters]
  );

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters({ page: 1, limit: defaultLimit });
  }, [setFilters, defaultLimit]);

  return {
    filters,
    setFilters,
    updateFilter,
    clearFilters,
  };
}
