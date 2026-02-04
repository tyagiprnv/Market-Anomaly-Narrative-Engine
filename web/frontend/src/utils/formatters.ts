/**
 * Utility functions for formatting data
 */

import { format, formatDistanceToNow } from 'date-fns';

export function formatDate(date: string | Date): string {
  return format(new Date(date), 'MMM d, yyyy h:mm a');
}

export function formatDateShort(date: string | Date): string {
  return format(new Date(date), 'MMM d, h:mm a');
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined) return 'N/A';
  return value.toFixed(decimals);
}

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(value);
}

export function formatLargeNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';

  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B`;
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M`;
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(2)}K`;
  }
  return value.toFixed(2);
}

export function formatSymbol(symbol: string): string {
  return symbol.replace('-USD', '');
}

export function getAnomalyTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    PRICE_SPIKE: 'Price Spike',
    PRICE_DROP: 'Price Drop',
    VOLUME_SPIKE: 'Volume Spike',
    COMBINED: 'Combined',
  };
  return labels[type] || type;
}

export function getAnomalyTypeColor(type: string): string {
  const colors: Record<string, string> = {
    PRICE_SPIKE: 'success',
    PRICE_DROP: 'danger',
    VOLUME_SPIKE: 'warning',
    COMBINED: 'info',
  };
  return colors[type] || 'neutral';
}

export function getValidationStatusColor(status: string): string {
  const colors: Record<string, string> = {
    VALID: 'success',
    INVALID: 'danger',
    UNVALIDATED: 'neutral',
  };
  return colors[status] || 'neutral';
}

export function getSentimentColor(sentiment: string | null): string {
  if (!sentiment) return 'neutral';
  const colors: Record<string, string> = {
    POSITIVE: 'success',
    NEGATIVE: 'danger',
    NEUTRAL: 'neutral',
  };
  return colors[sentiment] || 'neutral';
}

export function getTimingBadgeText(timing: string | null): string {
  if (!timing) return '';
  const labels: Record<string, string> = {
    BEFORE: 'Before',
    DURING: 'During',
    AFTER: 'After',
  };
  return labels[timing] || timing;
}
