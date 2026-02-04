/**
 * Filter persistence utilities using localStorage
 */

import { AnomalyFilters } from '@mane/shared/types/api';

const STORAGE_KEY = 'mane:anomaly-filters';

/**
 * Save filters to localStorage
 */
export function saveFilters(filters: AnomalyFilters): void {
  try {
    // Don't save page and limit (ephemeral)
    const { page, limit, ...persistentFilters } = filters;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persistentFilters));
  } catch (error) {
    console.error('Failed to save filters to localStorage:', error);
  }
}

/**
 * Load filters from localStorage
 */
export function loadFilters(): Partial<AnomalyFilters> | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return null;
    }
    return JSON.parse(stored);
  } catch (error) {
    console.error('Failed to load filters from localStorage:', error);
    return null;
  }
}

/**
 * Clear saved filters
 */
export function clearStoredFilters(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear filters from localStorage:', error);
  }
}

/**
 * Check if there are saved filters
 */
export function hasSavedFilters(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== null;
  } catch (error) {
    return false;
  }
}
