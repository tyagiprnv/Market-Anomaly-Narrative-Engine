/**
 * Pagination utility functions
 */

import { PaginationMeta } from '@mane/shared';

export interface PaginationParams {
  page: number;
  limit: number;
}

export function calculatePagination(
  page: number,
  limit: number,
  total: number
): PaginationMeta {
  const totalPages = Math.ceil(total / limit);

  return {
    page,
    limit,
    total,
    totalPages,
    hasNext: page < totalPages,
    hasPrev: page > 1,
  };
}

export function parsePaginationParams(
  page?: string | number,
  limit?: string | number
): PaginationParams {
  const parsedPage = Math.max(1, Number(page) || 1);
  const parsedLimit = Math.min(100, Math.max(1, Number(limit) || 20));

  return {
    page: parsedPage,
    limit: parsedLimit,
  };
}

export function calculateSkip(page: number, limit: number): number {
  return (page - 1) * limit;
}
