/**
 * List component for displaying multiple anomalies
 */

import { AnomalyDTO } from '@mane/shared/types/api';
import { AnomalyCard } from './AnomalyCard';

interface AnomalyListProps {
  anomalies: AnomalyDTO[];
  onAnomalyClick?: (anomaly: AnomalyDTO) => void;
  emptyMessage?: string;
}

export function AnomalyList({
  anomalies,
  onAnomalyClick,
  emptyMessage = 'No anomalies found',
}: AnomalyListProps) {
  if (anomalies.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
          <svg
            className="w-8 h-8 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
        </div>
        <p className="text-gray-600 text-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {anomalies.map((anomaly) => (
        <AnomalyCard
          key={anomaly.id}
          anomaly={anomaly}
          onClick={onAnomalyClick ? () => onAnomalyClick(anomaly) : undefined}
        />
      ))}
    </div>
  );
}
