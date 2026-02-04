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

interface AnomalyCardProps {
  anomaly: AnomalyDTO;
  onClick?: () => void;
}

export function AnomalyCard({ anomaly, onClick }: AnomalyCardProps) {
  const typeColor = getAnomalyTypeColor(anomaly.type);
  const validationColor = getValidationStatusColor(anomaly.validation_status || 'UNVALIDATED');

  const bgColorMap = {
    success: 'bg-green-50 border-green-200',
    danger: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200',
    info: 'bg-blue-50 border-blue-200',
    neutral: 'bg-gray-50 border-gray-200',
  };

  const badgeColorMap = {
    success: 'bg-green-100 text-green-800',
    danger: 'bg-red-100 text-red-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
    neutral: 'bg-gray-100 text-gray-800',
  };

  return (
    <div
      className={`border rounded-lg p-4 ${bgColorMap[typeColor]} ${
        onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''
      }`}
      onClick={onClick}
    >
      {/* Header: Symbol and Type */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-gray-900">{formatSymbol(anomaly.symbol)}</span>
          <span className={`px-2 py-1 rounded text-xs font-medium ${badgeColorMap[typeColor]}`}>
            {getAnomalyTypeLabel(anomaly.type)}
          </span>
        </div>
        <span className="text-xs text-gray-500">{formatRelativeTime(anomaly.timestamp)}</span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div className="text-xs text-gray-600">Price</div>
          <div className="text-sm font-semibold text-gray-900">{formatPrice(anomaly.price)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Return</div>
          <div
            className={`text-sm font-semibold ${
              (anomaly.price_return || 0) > 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {formatPercent(anomaly.price_return)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Z-Score</div>
          <div className="text-sm font-semibold text-gray-900">
            {anomaly.z_score?.toFixed(2) || 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Confidence</div>
          <div className="text-sm font-semibold text-gray-900">
            {((anomaly.confidence || 0) * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Narrative (if exists) */}
      {anomaly.narrative?.narrative_text && (
        <div className="mb-3 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-1">Narrative</div>
          <p className="text-sm text-gray-800 line-clamp-2">{anomaly.narrative.narrative_text}</p>
        </div>
      )}

      {/* Footer: Validation and Metadata */}
      <div className="flex justify-between items-center pt-3 border-t border-gray-200">
        <div className="flex items-center gap-2">
          {anomaly.validation_status && (
            <span className={`px-2 py-1 rounded text-xs font-medium ${badgeColorMap[validationColor]}`}>
              {anomaly.validation_status}
            </span>
          )}
          {anomaly.detection_metadata?.timeframe_minutes && (
            <span className="text-xs text-gray-600">
              {anomaly.detection_metadata.timeframe_minutes}min window
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">{formatDateShort(anomaly.timestamp)}</div>
      </div>
    </div>
  );
}
