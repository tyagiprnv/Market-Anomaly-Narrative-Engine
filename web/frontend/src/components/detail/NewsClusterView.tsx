/**
 * Component for displaying news clusters with their articles
 */

import { NewsClusterDTO, NewsArticleDTO } from '@mane/shared/types/database';
import { NewsArticleCard } from './NewsArticleCard';
import { getSentimentColor } from '../../utils/formatters';

interface NewsClusterViewProps {
  clusters: NewsClusterDTO[];
  unclustered: NewsArticleDTO[];
}

export function NewsClusterView({ clusters, unclustered }: NewsClusterViewProps) {
  if (clusters.length === 0 && unclustered.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Related News</h2>
        <p className="text-gray-600">No news articles found for this anomaly.</p>
      </div>
    );
  }

  const badgeColorMap = {
    success: 'bg-green-100 text-green-800',
    danger: 'bg-red-100 text-red-800',
    neutral: 'bg-gray-100 text-gray-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Related News</h2>

      {/* Clustered articles */}
      {clusters.map((cluster) => (
        <div key={cluster.id} className="mb-6 last:mb-0">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-lg font-medium text-gray-900">{cluster.clusterLabel}</h3>
            <span className="text-sm text-gray-600">
              ({cluster.articleCount} {cluster.articleCount === 1 ? 'article' : 'articles'})
            </span>
            {cluster.averageSentiment && (
              <span className={`text-xs px-2 py-0.5 rounded ${badgeColorMap[getSentimentColor(cluster.averageSentiment)]}`}>
                {cluster.averageSentiment}
              </span>
            )}
          </div>

          <div className="space-y-2">
            {cluster.articles?.map((article) => (
              <NewsArticleCard key={article.id} article={article} />
            ))}
          </div>
        </div>
      ))}

      {/* Unclustered articles */}
      {unclustered.length > 0 && (
        <div className={clusters.length > 0 ? 'mt-6 pt-6 border-t border-gray-200' : ''}>
          <h3 className="text-lg font-medium text-gray-900 mb-3">
            Other Articles ({unclustered.length})
          </h3>
          <div className="space-y-2">
            {unclustered.map((article) => (
              <NewsArticleCard key={article.id} article={article} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
