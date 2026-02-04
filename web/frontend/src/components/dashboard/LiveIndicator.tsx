/**
 * Live indicator showing connection status and last update time
 */

import { formatRelativeTime } from '../../utils/formatters';

interface LiveIndicatorProps {
  lastUpdate: Date | null;
  isPolling: boolean;
  className?: string;
}

export function LiveIndicator({ lastUpdate, isPolling, className = '' }: LiveIndicatorProps) {
  return (
    <div className={`flex items-center gap-2 text-sm ${className}`}>
      {/* Status dot */}
      <div className="flex items-center gap-1.5">
        <div
          className={`w-2 h-2 rounded-full ${
            isPolling ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
          }`}
        />
        <span className={`font-medium ${isPolling ? 'text-green-700' : 'text-gray-600'}`}>
          {isPolling ? 'Live' : 'Paused'}
        </span>
      </div>

      {/* Last update time */}
      {lastUpdate && (
        <>
          <span className="text-gray-400">•</span>
          <span className="text-gray-600">Updated {formatRelativeTime(lastUpdate)}</span>
        </>
      )}
    </div>
  );
}
