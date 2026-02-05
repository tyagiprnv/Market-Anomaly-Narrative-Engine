/**
 * Main dashboard page showing live anomalies
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLatestAnomalies } from '../api/queries/anomalies';
import { AnomalyList } from '../components/dashboard/AnomalyList';
import { SymbolSelector } from '../components/dashboard/SymbolSelector';
import { LiveIndicator } from '../components/dashboard/LiveIndicator';
import { ListSkeleton, AnomalyCardSkeleton, NoAnomaliesYet, NoAnomaliesFound } from '../components/common';
import { AppLayout } from '../components/layout/AppLayout';
import { AnomalyDTO } from '@mane/shared/types/api';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

export function Dashboard() {
  useDocumentTitle('Dashboard');
  const navigate = useNavigate();
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch latest anomalies with 30-second polling
  const { data: latestAnomalies = [], isLoading, isFetching } = useLatestAnomalies(
    {
      symbols: selectedSymbols.length > 0 ? selectedSymbols : undefined,
    },
    {
      refetchInterval: 30_000, // 30 seconds
    }
  );

  // Update last update time when data changes
  useEffect(() => {
    if (!isFetching && latestAnomalies.length > 0) {
      setLastUpdate(new Date());
    }
  }, [latestAnomalies, isFetching]);

  const handleAnomalyClick = (anomaly: AnomalyDTO) => {
    console.log('Anomaly clicked:', anomaly.id);
    console.log('Navigating to:', `/anomalies/${anomaly.id}`);
    navigate(`/anomalies/${anomaly.id}`);
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-gray-100">Live Anomaly Feed</h2>
            <p className="mt-1 text-sm text-gray-400">
              Real-time detection of crypto market anomalies
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => navigate('/history')}
                className="px-3 sm:px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors text-sm font-medium whitespace-nowrap"
              >
                Browse History
              </button>
              <button
                onClick={() => navigate('/charts')}
                className="px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
              >
                View Charts
              </button>
            </div>
            <LiveIndicator lastUpdate={lastUpdate} isPolling={!isFetching} />
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Filter by Symbol
          </label>
          <SymbolSelector selected={selectedSymbols} onChange={setSelectedSymbols} />
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <ListSkeleton count={6} ItemSkeleton={AnomalyCardSkeleton} />
          </div>
        )}

        {/* Anomaly list */}
        {!isLoading && (
          <AnomalyList
            anomalies={latestAnomalies}
            onAnomalyClick={handleAnomalyClick}
            emptyState={
              selectedSymbols.length > 0 ? (
                <NoAnomaliesFound />
              ) : (
                <NoAnomaliesYet />
              )
            }
          />
        )}
      </div>
    </AppLayout>
  );
}
