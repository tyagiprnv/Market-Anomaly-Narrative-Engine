/**
 * Price chart component using TradingView Lightweight Charts
 */

import { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, LineData, UTCTimestamp } from 'lightweight-charts';
import { AnomalyDTO } from '@mane/shared/types/database';

interface PriceChartProps {
  /** Price data points */
  data: Array<{
    timestamp: number;
    price: number;
    volume: number | null;
  }>;
  /** Symbol being displayed */
  symbol: string;
  /** Anomalies to mark on the chart (optional) */
  anomalies?: AnomalyDTO[];
  /** Chart height in pixels */
  height?: number;
  /** Loading state */
  isLoading?: boolean;
}

export function PriceChart({
  data,
  symbol,
  anomalies = [],
  height = 400,
  isLoading = false,
}: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || isLoading || data.length === 0) {
      return;
    }

    try {
      // Create chart instance
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height,
        layout: {
          background: { color: '#1a1a1a' },
          textColor: '#d1d5db',
        },
        grid: {
          vertLines: { color: '#2a2a2a' },
          horzLines: { color: '#2a2a2a' },
        },
        rightPriceScale: {
          borderColor: '#2a2a2a',
        },
        timeScale: {
          borderColor: '#2a2a2a',
          timeVisible: true,
          secondsVisible: false,
        },
        crosshair: {
          mode: 1, // Normal crosshair
          vertLine: {
            width: 1,
            color: '#6b7280',
            style: 2, // Dashed
          },
          horzLine: {
            width: 1,
            color: '#6b7280',
            style: 2, // Dashed
          },
        },
      });

      chartRef.current = chart;

      // Create line series
      const lineSeries = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });

      lineSeriesRef.current = lineSeries;

      // Convert data to chart format and ensure ascending order
      const chartData: LineData[] = data
        .map((d) => ({
          time: (d.timestamp / 1000) as UTCTimestamp, // Convert ms to seconds
          value: d.price,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number)); // Sort ascending by time

      lineSeries.setData(chartData);

      // Add anomaly markers
      if (anomalies.length > 0) {
        const markers = anomalies
          .filter((a) => {
            // Only show anomalies that fall within the chart's time range
            const anomalyTime = new Date(a.detectedAt).getTime() / 1000;
            const chartStart = Number(chartData[0]?.time ?? 0);
            const chartEnd = Number(chartData[chartData.length - 1]?.time ?? 0);
            return anomalyTime >= chartStart && anomalyTime <= chartEnd;
          })
          .map((a) => {
            const isPositive = (a.metrics.priceChangePct ?? 0) > 0;
            return {
              time: (new Date(a.detectedAt).getTime() / 1000) as UTCTimestamp,
              position: (isPositive ? 'aboveBar' : 'belowBar') as 'aboveBar' | 'belowBar',
              color: isPositive ? '#10b981' : '#ef4444',
              shape: 'circle' as const,
              text: `${a.anomalyType}${a.detectionMetadata?.timeframe_minutes ? ` (${a.detectionMetadata.timeframe_minutes}m)` : ''}`,
              size: 1,
            };
          })
          .sort((a, b) => (a.time as number) - (b.time as number)); // Sort markers by time

        lineSeries.setMarkers(markers);
      }

      // Fit content to view
      chart.timeScale().fitContent();

      // Handle window resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }
      };
    } catch (err) {
      console.error('Error creating chart:', err);
      setError(err instanceof Error ? err.message : 'Failed to create chart');
    }
  }, [data, anomalies, height, isLoading]);

  if (error) {
    return (
      <div
        className="flex items-center justify-center bg-gray-900 border border-gray-800 rounded-lg"
        style={{ height }}
      >
        <div className="text-center">
          <p className="text-red-400 font-semibold">Chart Error</p>
          <p className="text-gray-400 text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center bg-gray-900 border border-gray-800 rounded-lg"
        style={{ height }}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-400 text-sm mt-2">Loading chart...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-900 border border-gray-800 rounded-lg"
        style={{ height }}
      >
        <div className="text-center">
          <p className="text-gray-400">No price data available for {symbol}</p>
          <p className="text-gray-500 text-sm mt-1">Try selecting a different time range</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        ref={chartContainerRef}
        className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden"
      />
      {anomalies.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          {anomalies.length} anomal{anomalies.length === 1 ? 'y' : 'ies'} marked on chart
        </div>
      )}
    </div>
  );
}
