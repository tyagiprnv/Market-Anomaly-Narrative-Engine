/**
 * Main dashboard page showing live anomalies
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLatestAnomalies, useAnomalyStats } from '../api/queries/anomalies';
import { AnomalyList } from '../components/dashboard/AnomalyList';
import { SymbolSelector } from '../components/dashboard/SymbolSelector';
import { LiveIndicator } from '../components/dashboard/LiveIndicator';
import { AppLayout } from '../components/layout/AppLayout';
import { AnomalyDTO } from '@mane/shared/types/api';

export function Dashboard() {
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

  // Fetch stats for summary
  const { data: stats } = useAnomalyStats(
    {
      symbols: selectedSymbols.length > 0 ? selectedSymbols : undefined,
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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-100">Live Anomaly Feed</h2>
            <p className="mt-1 text-sm text-gray-400">
              Real-time detection of crypto market anomalies
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/history')}
              className="px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors text-sm font-medium"
            >
              Browse History
            </button>
            <button
              onClick={() => navigate('/charts')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              View Charts
            </button>
            <LiveIndicator lastUpdate={lastUpdate} isPolling={!isFetching} />
          </div>
        </div>

        {/* Filters and Stats */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Symbol selector */}
            <div className="lg:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Symbol
              </label>
              <SymbolSelector selected={selectedSymbols} onChange={setSelectedSymbols} />
            </div>

            {/* Stats */}
            {stats && (
              <>
                <div className="flex flex-col">
                  <span className="text-sm text-gray-600">Total Anomalies</span>
                  <span className="text-2xl font-bold text-gray-900">{stats.totalAnomalies}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-sm text-gray-600">Avg Confidence</span>
                  <span className="text-2xl font-bold text-gray-900">
                    {(stats.averageConfidence * 100).toFixed(0)}%
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
            <p className="text-gray-600">Loading anomalies...</p>
          </div>
        )}

        {/* Anomaly list */}
        {!isLoading && (
          <AnomalyList
            anomalies={latestAnomalies}
            onAnomalyClick={handleAnomalyClick}
            emptyMessage={
              selectedSymbols.length > 0
                ? 'No anomalies found for selected symbols'
                : 'No anomalies detected yet. The system is monitoring markets...'
            }
          />
        )}
      </div>
    </AppLayout>
  );
}
