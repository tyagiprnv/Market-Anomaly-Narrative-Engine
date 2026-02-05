/**
 * Full-screen chart view page
 */

import { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { PriceChart, TimeRangeSelector, TimeRange, TIME_RANGES } from '../components/charts';
import { usePriceHistory } from '../api/queries';
import { useAnomalies } from '../api/queries';
import { SUPPORTED_SYMBOLS, SYMBOL_NAMES, isValidSymbol, SupportedSymbol } from '@mane/shared/constants/symbols';

export function ChartView() {
  const navigate = useNavigate();
  const { symbol: urlSymbol } = useParams<{ symbol: string }>();

  // Validate and set initial symbol
  const initialSymbol = urlSymbol && isValidSymbol(urlSymbol) ? urlSymbol : 'BTC-USD';
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol);
  const [selectedRange, setSelectedRange] = useState<TimeRange>(TIME_RANGES[2]); // Default to 24H

  // Calculate date range based on selected time range
  const { startDate, endDate } = useMemo(() => {
    const end = new Date();
    const start = new Date(end.getTime() - selectedRange.hours * 60 * 60 * 1000);
    return {
      startDate: start.toISOString(),
      endDate: end.toISOString(),
    };
  }, [selectedRange]);

  // Fetch price data with 30-second polling for live updates
  const { data: priceData, isLoading: isPriceLoading } = usePriceHistory(
    {
      symbol: selectedSymbol,
      startDate,
      endDate,
      granularity: selectedRange.granularity,
    },
    {
      refetchInterval: 30_000, // Poll every 30 seconds for new price data
    }
  );

  // Fetch anomalies for the selected symbol and time range
  const { data: anomaliesData } = useAnomalies({
    symbols: [selectedSymbol],
    startDate,
    endDate,
    limit: 100,
  });

  const anomalies = anomaliesData?.data ?? [];

  // Handle symbol change
  const handleSymbolChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSymbol = e.target.value as SupportedSymbol;
    setSelectedSymbol(newSymbol);
    // Update URL
    navigate(`/charts/${newSymbol}`, { replace: true });
  };

  return (
    <AppLayout>
      <div className="min-h-screen bg-gray-950">
        {/* Header */}
        <div className="bg-gray-900 border-b border-gray-800 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="text-gray-400 hover:text-gray-300 transition-colors"
              >
                ← Back to Dashboard
              </button>
              <div className="h-6 w-px bg-gray-700" />
              <h1 className="text-xl font-semibold text-white">Price Chart</h1>
            </div>
            <div className="flex items-center gap-4">
              <TimeRangeSelector selected={selectedRange} onChange={setSelectedRange} />
              <select
                value={selectedSymbol}
                onChange={handleSymbolChange}
                className="bg-gray-800 text-white border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {SUPPORTED_SYMBOLS.map((symbol) => (
                  <option key={symbol} value={symbol}>
                    {SYMBOL_NAMES[symbol]} ({symbol})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="p-6">
          <PriceChart
            data={priceData?.data ?? []}
            symbol={selectedSymbol}
            anomalies={anomalies}
            height={600}
            isLoading={isPriceLoading}
          />

          {/* Chart info */}
          {priceData?.data && (
            <div className="mt-4 text-sm text-gray-500">
              <p>
                Showing {priceData.data.length} data points at {priceData.granularity} granularity
              </p>
              <p>
                Time range: {new Date(startDate).toLocaleString()} to{' '}
                {new Date(endDate).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
