/**
 * Panel component for displaying anomaly metrics and metadata
 */

import { AnomalyDTO } from '@mane/shared/types/database';
import {
  formatDate,
  formatPrice,
  formatPercent,
  formatNumber,
  formatSymbol,
  getAnomalyTypeLabel,
  getAnomalyTypeColor,
} from '../../utils/formatters';

interface AnomalyDetailPanelProps {
  anomaly: AnomalyDTO;
}

export function AnomalyDetailPanel({ anomaly }: AnomalyDetailPanelProps) {
  const typeColor = getAnomalyTypeColor(anomaly.anomalyType);

  const badgeColorMap = {
    success: 'bg-green-100 text-green-800',
    danger: 'bg-red-100 text-red-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
    neutral: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {formatSymbol(anomaly.symbol)}
          </h1>
          <p className="text-gray-600">{formatDate(anomaly.detectedAt)}</p>
        </div>
        <span className={`px-3 py-1 rounded text-sm font-medium ${badgeColorMap[typeColor]}`}>
          {getAnomalyTypeLabel(anomaly.anomalyType)}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <MetricCard
          label="Price at Detection"
          value={formatPrice(anomaly.priceSnapshot.atDetection)}
        />
        <MetricCard
          label="Price Before"
          value={formatPrice(anomaly.priceSnapshot.before)}
        />
        <MetricCard
          label="Price Change"
          value={formatPercent(anomaly.metrics.priceChangePct)}
          valueColor={
            anomaly.metrics.priceChangePct && anomaly.metrics.priceChangePct > 0
              ? 'text-green-600'
              : 'text-red-600'
          }
        />
        <MetricCard
          label="Z-Score"
          value={formatNumber(anomaly.metrics.zScore)}
        />
        <MetricCard
          label="Volume Change"
          value={formatPercent(anomaly.metrics.volumeChangePct)}
        />
        <MetricCard
          label="Confidence"
          value={formatPercent(anomaly.metrics.confidence * 100)}
        />
      </div>

      {/* Detection Metadata */}
      {anomaly.detectionMetadata && (
        <div className="pt-6 border-t border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Detection Metadata</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {anomaly.detectionMetadata.detector && (
              <div>
                <span className="text-gray-600">Detector:</span>{' '}
                <span className="font-medium text-gray-900">
                  {anomaly.detectionMetadata.detector}
                </span>
              </div>
            )}
            {anomaly.detectionMetadata.timeframe_minutes && (
              <div>
                <span className="text-gray-600">Timeframe:</span>{' '}
                <span className="font-medium text-gray-900">
                  {anomaly.detectionMetadata.timeframe_minutes} minutes
                </span>
              </div>
            )}
            {anomaly.detectionMetadata.volatility_tier && (
              <div>
                <span className="text-gray-600">Volatility Tier:</span>{' '}
                <span className="font-medium text-gray-900">
                  {anomaly.detectionMetadata.volatility_tier}
                </span>
              </div>
            )}
            {anomaly.detectionMetadata.asset_threshold && (
              <div>
                <span className="text-gray-600">Threshold:</span>{' '}
                <span className="font-medium text-gray-900">
                  {anomaly.detectionMetadata.asset_threshold.toFixed(2)}
                </span>
              </div>
            )}
            {anomaly.detectionMetadata.threshold_source && (
              <div>
                <span className="text-gray-600">Source:</span>{' '}
                <span className="font-medium text-gray-900">
                  {anomaly.detectionMetadata.threshold_source}
                </span>
              </div>
            )}
            <div>
              <span className="text-gray-600">Baseline Window:</span>{' '}
              <span className="font-medium text-gray-900">
                {anomaly.baselineWindowMinutes} minutes
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  valueColor?: string;
}

function MetricCard({ label, value, valueColor = 'text-gray-900' }: MetricCardProps) {
  return (
    <div>
      <div className="text-xs text-gray-600 mb-1">{label}</div>
      <div className={`text-lg font-semibold ${valueColor}`}>{value}</div>
    </div>
  );
}
