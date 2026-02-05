/**
 * Anomaly detail page - shows full information about a single anomaly
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useAnomaly } from '../api/queries/anomalies';
import { usePriceHistory } from '../api/queries/prices';
import { AppLayout } from '../components/layout/AppLayout';
import {
  AnomalyDetailPanel,
  NarrativeDisplay,
  NewsClusterView,
} from '../components/detail';
import { PriceChart } from '../components/charts';
import { AnomalyDetailSkeleton, ChartSkeleton, ErrorState } from '../components/common';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

export function AnomalyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: anomaly, isLoading, error } = useAnomaly(id || '', { enabled: !!id });

  useDocumentTitle(anomaly ? `${anomaly.symbol} Anomaly` : 'Anomaly Details');

  // Calculate date ranges for price history (needs to be before conditional returns for hooks)
  const anomalyTime = anomaly ? new Date(anomaly.detectedAt) : new Date();
  const startDate = new Date(anomalyTime.getTime() - 6 * 60 * 60 * 1000).toISOString(); // 6 hours before
  const endDate = new Date(anomalyTime.getTime() + 1 * 60 * 60 * 1000).toISOString(); // 1 hour after

  // Fetch price history with polling - must be called before any conditional returns (React Rules of Hooks)
  const { data: priceData, isLoading: isPriceLoading } = usePriceHistory(
    {
      symbol: anomaly?.symbol || '',
      startDate,
      endDate,
      granularity: '5m', // 5-minute granularity for detailed view
    },
    {
      enabled: !!anomaly, // Only fetch when anomaly data is loaded
      refetchInterval: 30_000, // Poll every 30 seconds for live updates
    }
  );

  if (isLoading) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <AnomalyDetailSkeleton />
          <ChartSkeleton />
        </div>
      </AppLayout>
    );
  }

  if (error || !anomaly) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto">
          <ErrorState
            message={error ? 'Failed to load anomaly details' : 'Anomaly not found'}
            onRetry={() => navigate('/')}
          />
        </div>
      </AppLayout>
    );
  }

  // Separate clustered and unclustered articles
  const clustersWithArticles = (anomaly.newsClusters || []).map((cluster) => ({
    ...cluster,
    articles: (anomaly.newsArticles || []).filter(
      (article) => article.clusterId === cluster.id
    ),
  }));

  const unclusteredArticles = (anomaly.newsArticles || []).filter(
    (article) => !article.clusterId
  );

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate('/')}
          className="mb-4 text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1 text-sm sm:text-base"
        >
          <span>←</span>
          <span>Back to Dashboard</span>
        </button>

        {/* Main content */}
        <div className="space-y-4 sm:space-y-6">
          {/* Anomaly metrics and metadata */}
          <AnomalyDetailPanel anomaly={anomaly} />

          {/* Price chart */}
          <div className="bg-white rounded-lg shadow p-4 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <h2 className="text-base sm:text-lg font-semibold text-gray-900">Price Context</h2>
              <button
                onClick={() => navigate(`/charts/${anomaly.symbol}`)}
                className="text-sm text-blue-600 hover:text-blue-800 transition-colors self-start sm:self-auto whitespace-nowrap"
              >
                View full chart →
              </button>
            </div>
            <PriceChart
              data={priceData?.data ?? []}
              symbol={anomaly.symbol}
              anomalies={[anomaly]}
              height={300}
              isLoading={isPriceLoading}
            />
            <p className="mt-2 text-xs text-gray-500">
              Showing 6 hours before to 1 hour after the anomaly
            </p>
          </div>

          {/* Narrative (if exists) */}
          {anomaly.narrative && <NarrativeDisplay narrative={anomaly.narrative} />}

          {/* News clusters */}
          <NewsClusterView
            clusters={clustersWithArticles}
            unclustered={unclusteredArticles}
          />
        </div>
      </div>
    </AppLayout>
  );
}
