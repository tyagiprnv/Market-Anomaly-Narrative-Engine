/**
 * Reusable empty state component
 * Shows icon, title, description, and optional action button
 */

import React from 'react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

/**
 * Default icons for common empty states
 */
export const EmptyStateIcons = {
  NoData: (
    <svg
      className="w-12 h-12 text-gray-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    </svg>
  ),
  NoResults: (
    <svg
      className="w-12 h-12 text-gray-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  NoAnomalies: (
    <svg
      className="w-12 h-12 text-gray-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  NoNews: (
    <svg
      className="w-12 h-12 text-gray-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
    </svg>
  ),
  Error: (
    <svg
      className="w-12 h-12 text-red-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  Monitoring: (
    <svg
      className="w-12 h-12 text-blue-400"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
};

export function EmptyState({ icon, title, description, action, className = '' }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
      {/* Icon */}
      {icon && (
        <div className="mb-4 flex items-center justify-center">
          {icon}
        </div>
      )}

      {/* Title */}
      <h3 className="text-base sm:text-lg font-medium text-gray-100 mb-2 max-w-md">
        {title}
      </h3>

      {/* Description */}
      {description && (
        <p className="text-sm text-gray-400 max-w-md mb-4">
          {description}
        </p>
      )}

      {/* Action Button */}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

/**
 * Specific empty state variants for common use cases
 */

export function NoAnomaliesFound({ onClearFilters }: { onClearFilters?: () => void }) {
  return (
    <EmptyState
      icon={EmptyStateIcons.NoAnomalies}
      title="No anomalies found"
      description="Try adjusting your filters or date range to find more results."
      action={onClearFilters ? { label: 'Clear Filters', onClick: onClearFilters } : undefined}
    />
  );
}

export function NoAnomaliesYet() {
  return (
    <EmptyState
      icon={EmptyStateIcons.Monitoring}
      title="No anomalies detected yet"
      description="The system is actively monitoring markets. New anomalies will appear here as they are detected."
    />
  );
}

export function NoNewsArticles() {
  return (
    <EmptyState
      icon={EmptyStateIcons.NoNews}
      title="No news articles"
      description="No related news articles were found for this anomaly."
    />
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <EmptyState
      icon={EmptyStateIcons.Error}
      title="Something went wrong"
      description={message || 'An unexpected error occurred. Please try again.'}
      action={onRetry ? { label: 'Try Again', onClick: onRetry } : undefined}
    />
  );
}
