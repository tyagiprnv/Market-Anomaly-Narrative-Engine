/**
 * Card component for displaying a single news article
 */

import { NewsArticleDTO } from '@mane/shared/types/database';
import { formatDate, getSentimentColor, getTimingBadgeText } from '../../utils/formatters';

interface NewsArticleCardProps {
  article: NewsArticleDTO;
}

export function NewsArticleCard({ article }: NewsArticleCardProps) {
  const sentimentColor = getSentimentColor(article.sentiment);
  const timingText = getTimingBadgeText(article.timing);

  const badgeColorMap = {
    success: 'bg-green-100 text-green-800',
    danger: 'bg-red-100 text-red-800',
    neutral: 'bg-gray-100 text-gray-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-900 font-medium hover:text-blue-600 transition-colors flex-1"
        >
          {article.title}
        </a>
      </div>

      <div className="flex items-center gap-2 flex-wrap text-xs text-gray-600">
        <span className="font-medium">{article.source}</span>
        <span>•</span>
        <span>{formatDate(article.publishedAt)}</span>

        {article.sentiment && (
          <>
            <span>•</span>
            <span className={`px-2 py-0.5 rounded ${badgeColorMap[sentimentColor]}`}>
              {article.sentiment}
            </span>
          </>
        )}

        {article.timing && (
          <>
            <span>•</span>
            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800">
              {timingText}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
