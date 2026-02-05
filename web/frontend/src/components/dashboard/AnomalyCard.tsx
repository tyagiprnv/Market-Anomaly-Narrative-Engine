/**
 * Card component for displaying a single anomaly
 */

import { AnomalyDTO } from '@mane/shared/types/api';
import {
  formatDateShort,
  formatRelativeTime,
  formatPercent,
  formatPrice,
  formatSymbol,
  getAnomalyTypeLabel,
  getAnomalyTypeColor,
  getValidationStatusColor,
} from '../../utils/formatters';
import { bgColorMap, badgeColorMap, getColor } from '../../utils/colors';

interface AnomalyCardProps {
  anomaly: AnomalyDTO;
  onClick?: () => void;
}

export function AnomalyCard({ anomaly, onClick }: AnomalyCardProps) {
  console.log('AnomalyCard rendered:', { id: anomaly.id, hasOnClick: !!onClick });

  const typeColor = getColor(getAnomalyTypeColor(anomaly.anomalyType));
  const validationColor = getColor(getValidationStatusColor(anomaly.narrative?.validationStatus || 'NOT_GENERATED'));

  return (
    <div
      className={`border rounded-lg p-4 ${bgColorMap[typeColor]} ${
        onClick ? 'cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all' : ''
      }`}
      onClick={(e) => {
        console.log('Card clicked!', anomaly.id);
        if (onClick) {
          onClick();
        }
      }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header: Symbol and Type */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-gray-900">{formatSymbol(anomaly.symbol)}</span>
          <span className={`px-2 py-1 rounded text-xs font-medium ${badgeColorMap[typeColor]}`}>
            {getAnomalyTypeLabel(anomaly.anomalyType)}
          </span>
        </div>
        <span className="text-xs text-gray-500">{formatRelativeTime(anomaly.detectedAt)}</span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div className="text-xs text-gray-600">Price</div>
          <div className="text-sm font-semibold text-gray-900">{formatPrice(anomaly.priceSnapshot.atDetection)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Return</div>
          <div
            className={`text-sm font-semibold ${
              (anomaly.metrics.priceChangePct || 0) > 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {formatPercent(anomaly.metrics.priceChangePct)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Z-Score</div>
          <div className="text-sm font-semibold text-gray-900">
            {anomaly.metrics.zScore?.toFixed(2) || 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Confidence</div>
          <div className="text-sm font-semibold text-gray-900">
            {((anomaly.metrics.confidence || 0) * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Narrative (if exists) */}
      {anomaly.narrative?.narrative && (
        <div className="mb-3 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-1">Narrative</div>
          <p className="text-sm text-gray-800 line-clamp-2">{anomaly.narrative.narrative}</p>
        </div>
      )}

      {/* Footer: Validation and Metadata */}
      <div className="flex justify-between items-center pt-3 border-t border-gray-200">
        <div className="flex items-center gap-2">
          {anomaly.narrative?.validationStatus && (
            <span className={`px-2 py-1 rounded text-xs font-medium ${badgeColorMap[validationColor]}`}>
              {anomaly.narrative.validationStatus}
            </span>
          )}
          {anomaly.detectionMetadata?.timeframe_minutes && (
            <span className="text-xs text-gray-600">
              {anomaly.detectionMetadata.timeframe_minutes}min window
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">{formatDateShort(anomaly.detectedAt)}</div>
      </div>
    </div>
  );
}
