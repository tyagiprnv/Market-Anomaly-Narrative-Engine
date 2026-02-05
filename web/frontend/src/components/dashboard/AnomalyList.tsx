/**
 * List component for displaying multiple anomalies
 */

import React from 'react';
import { AnomalyDTO } from '@mane/shared/types/api';
import { AnomalyCard } from './AnomalyCard';
import { EmptyState, EmptyStateIcons } from '../common';

interface AnomalyListProps {
  anomalies: AnomalyDTO[];
  onAnomalyClick?: (anomaly: AnomalyDTO) => void;
  emptyMessage?: string;
  emptyState?: React.ReactNode;
}

export function AnomalyList({
  anomalies,
  onAnomalyClick,
  emptyMessage = 'No anomalies found',
  emptyState,
}: AnomalyListProps) {
  if (anomalies.length === 0) {
    // Use custom empty state if provided, otherwise use default
    if (emptyState) {
      return <>{emptyState}</>;
    }

    return (
      <EmptyState
        icon={EmptyStateIcons.NoAnomalies}
        title="No anomalies found"
        description={emptyMessage}
      />
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
