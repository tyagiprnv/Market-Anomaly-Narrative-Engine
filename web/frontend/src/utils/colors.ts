/**
 * Color utility functions and mappings
 */

export type ColorVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral';

export const bgColorMap: Record<ColorVariant, string> = {
  success: 'bg-green-50 border-green-200',
  danger: 'bg-red-50 border-red-200',
  warning: 'bg-yellow-50 border-yellow-200',
  info: 'bg-blue-50 border-blue-200',
  neutral: 'bg-gray-50 border-gray-200',
};

export const badgeColorMap: Record<ColorVariant, string> = {
  success: 'bg-green-100 text-green-800',
  danger: 'bg-red-100 text-red-800',
  warning: 'bg-yellow-100 text-yellow-800',
  info: 'bg-blue-100 text-blue-800',
  neutral: 'bg-gray-100 text-gray-800',
};

export const borderColorMap: Record<ColorVariant, string> = {
  success: 'border-green-500',
  danger: 'border-red-500',
  warning: 'border-yellow-500',
  info: 'border-blue-500',
  neutral: 'border-gray-500',
};

export const textColorMap: Record<ColorVariant, string> = {
  success: 'text-green-600',
  danger: 'text-red-600',
  warning: 'text-yellow-600',
  info: 'text-blue-600',
  neutral: 'text-gray-600',
};

export const iconMap: Record<ColorVariant, string> = {
  success: '✓',
  danger: '✗',
  neutral: '?',
  warning: '!',
  info: 'ℹ',
};

/**
 * Get color with fallback to neutral
 */
export function getColor(color: string): ColorVariant {
  if (isColorVariant(color)) {
    return color;
  }
  return 'neutral';
}

function isColorVariant(value: string): value is ColorVariant {
  return ['success', 'danger', 'warning', 'info', 'neutral'].includes(value);
}
