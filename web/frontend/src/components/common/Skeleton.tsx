import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
}

/**
 * Base skeleton loader component
 * Shows animated placeholder while content loads
 */
export function Skeleton({
  className = '',
  variant = 'rectangular',
  width,
  height,
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded h-4',
    rectangular: 'rounded-lg',
    circular: 'rounded-full',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={`bg-gray-200 animate-pulse ${variantClasses[variant]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton loader for AnomalyCard
 */
export function AnomalyCardSkeleton() {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      {/* Header with symbol and type */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Skeleton className="w-20 h-5 mb-2 bg-gray-700" />
          <Skeleton className="w-32 h-4 bg-gray-700" />
        </div>
        <Skeleton className="w-20 h-6 rounded-full bg-gray-700" />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-3 mb-3 py-3 border-y border-gray-700">
        {[1, 2, 3, 4].map((i) => (
          <div key={i}>
            <Skeleton className="w-16 h-3 mb-2 bg-gray-700" />
            <Skeleton className="w-24 h-5 bg-gray-700" />
          </div>
        ))}
      </div>

      {/* Narrative */}
      <div className="mb-3">
        <Skeleton className="w-full h-4 mb-2 bg-gray-700" />
        <Skeleton className="w-3/4 h-4 bg-gray-700" />
      </div>

      {/* Footer with time and validation */}
      <div className="flex items-center justify-between text-sm">
        <Skeleton className="w-28 h-4 bg-gray-700" />
        <Skeleton className="w-16 h-5 rounded-full bg-gray-700" />
      </div>
    </div>
  );
}

/**
 * Skeleton loader for NewsArticleCard
 */
export function NewsArticleCardSkeleton() {
  return (
    <div className="bg-white rounded border border-gray-200 p-4">
      {/* Header with source and sentiment */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <Skeleton className="w-32 h-5 mb-2" />
          <Skeleton className="w-40 h-4" />
        </div>
        <Skeleton className="w-20 h-5 rounded-full" />
      </div>

      {/* Title */}
      <Skeleton className="w-full h-5 mb-2" />
      <Skeleton className="w-4/5 h-5 mb-3" />

      {/* Summary */}
      <Skeleton className="w-full h-4 mb-1" />
      <Skeleton className="w-full h-4 mb-1" />
      <Skeleton className="w-2/3 h-4 mb-3" />

      {/* Footer */}
      <div className="flex items-center justify-between">
        <Skeleton className="w-24 h-4" />
        <Skeleton className="w-16 h-4" />
      </div>
    </div>
  );
}

/**
 * Skeleton loader for AnomalyDetailPanel
 */
export function AnomalyDetailSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <Skeleton className="w-32 h-6 mb-2" />
          <Skeleton className="w-48 h-5" />
        </div>
        <Skeleton className="w-24 h-7 rounded-full" />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i}>
            <Skeleton className="w-20 h-4 mb-2" />
            <Skeleton className="w-28 h-6" />
          </div>
        ))}
      </div>

      {/* Narrative section */}
      <div className="border-t border-gray-200 pt-6 mb-6">
        <Skeleton className="w-32 h-5 mb-3" />
        <Skeleton className="w-full h-4 mb-2" />
        <Skeleton className="w-full h-4 mb-2" />
        <Skeleton className="w-3/4 h-4" />
      </div>

      {/* Detection metadata */}
      <div className="border-t border-gray-200 pt-6">
        <Skeleton className="w-40 h-5 mb-3" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i}>
              <Skeleton className="w-24 h-4 mb-2" />
              <Skeleton className="w-32 h-5" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for price chart
 */
export function ChartSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="w-32 h-6" />
        <Skeleton className="w-48 h-8 rounded-lg" />
      </div>
      <Skeleton className="w-full h-96 rounded-lg" />
    </div>
  );
}

/**
 * Skeleton loader for a list of items
 */
export function ListSkeleton({
  count = 3,
  ItemSkeleton = AnomalyCardSkeleton,
}: {
  count?: number;
  ItemSkeleton?: React.ComponentType;
}) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <ItemSkeleton key={i} />
      ))}
    </>
  );
}
