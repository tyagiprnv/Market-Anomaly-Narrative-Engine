/**
 * Time range selector for charts
 */

interface TimeRange {
  label: string;
  hours: number;
  granularity: '1m' | '5m' | '15m' | '1h';
}

const TIME_RANGES: TimeRange[] = [
  { label: '1H', hours: 1, granularity: '1m' },
  { label: '6H', hours: 6, granularity: '5m' },
  { label: '24H', hours: 24, granularity: '5m' },
  { label: '7D', hours: 168, granularity: '1h' },
  { label: '30D', hours: 720, granularity: '1h' },
];

interface TimeRangeSelectorProps {
  selected: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangeSelector({ selected, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-2">
      {TIME_RANGES.map((range) => (
        <button
          key={range.label}
          onClick={() => onChange(range)}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            selected.label === range.label
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
          }`}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}

export { TIME_RANGES };
export type { TimeRange };
