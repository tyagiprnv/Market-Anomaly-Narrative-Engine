-- Add detection_metadata JSON column for multi-timeframe and asset-aware detection
-- This stores metadata about how the anomaly was detected

ALTER TABLE anomalies
ADD COLUMN IF NOT EXISTS detection_metadata JSONB;

COMMENT ON COLUMN anomalies.detection_metadata IS 'Metadata about anomaly detection (timeframe_minutes, volatility_tier, asset_threshold, threshold_source, detector)';
