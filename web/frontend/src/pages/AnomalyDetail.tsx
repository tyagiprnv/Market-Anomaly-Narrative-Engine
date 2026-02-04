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

export function AnomalyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: anomaly, isLoading, error } = useAnomaly(id || '', { enabled: !!id });

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading anomaly details...</div>
        </div>
      </AppLayout>
    );
  }

  if (error || !anomaly) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-64">
          <div className="text-red-600 mb-4">
            {error ? 'Failed to load anomaly' : 'Anomaly not found'}
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Back to Dashboard
          </button>
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

  // Fetch price history around the anomaly (6 hours before to 1 hour after)
  const anomalyTime = new Date(anomaly.detectedAt);
  const startDate = new Date(anomalyTime.getTime() - 6 * 60 * 60 * 1000).toISOString(); // 6 hours before
  const endDate = new Date(anomalyTime.getTime() + 1 * 60 * 60 * 1000).toISOString(); // 1 hour after

  const { data: priceData, isLoading: isPriceLoading } = usePriceHistory({
    symbol: anomaly.symbol,
    startDate,
    endDate,
    granularity: '5m', // 5-minute granularity for detailed view
  });

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate('/')}
          className="mb-4 text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1"
        >
          <span>←</span>
          <span>Back to Dashboard</span>
        </button>

        {/* Main content */}
        <div className="space-y-6">
          {/* Anomaly metrics and metadata */}
          <AnomalyDetailPanel anomaly={anomaly} />

          {/* Price chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Price Context</h2>
              <button
                onClick={() => navigate(`/charts/${anomaly.symbol}`)}
                className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
              >
                View full chart →
              </button>
            </div>
            <PriceChart
              data={priceData?.data ?? []}
              symbol={anomaly.symbol}
              anomalies={[anomaly]}
              height={400}
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
