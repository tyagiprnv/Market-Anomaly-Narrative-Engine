/**
 * Anomaly detail page - shows full information about a single anomaly
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useAnomaly } from '../api/queries/anomalies';
import { AppLayout } from '../components/layout/AppLayout';
import {
  AnomalyDetailPanel,
  NarrativeDisplay,
  NewsClusterView,
} from '../components/detail';

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
