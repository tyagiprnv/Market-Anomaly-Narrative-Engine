/**
 * Historical anomaly browser page with filtering and pagination
 */
import { useNavigate } from 'react-router-dom';
import { useAnomalies } from '../api/queries/anomalies';
import { useFilterState } from '../utils/urlState';
import { AnomalyFilters } from '../components/browser';
import { AnomalyList } from '../components/dashboard';
import { Pagination } from '../components/common';
import { AppLayout } from '../components/layout/AppLayout';
import { AnomalyDTO } from '@mane/shared/types/api';

export function HistoricalBrowser() {
  const navigate = useNavigate();
  const { filters, setFilters, updateFilter, clearFilters } = useFilterState(20);

  const handleAnomalyClick = (anomaly: AnomalyDTO) => {
    navigate(`/anomalies/${anomaly.id}`);
  };
  const { data, isLoading, isError, error } = useAnomalies(filters);

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-100 mb-2">Historical Anomalies</h1>
          <p className="text-gray-400">
            Browse and filter all detected price anomalies across all symbols and timeframes.
          </p>
        </div>

        {/* Layout: Filters sidebar + Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            <AnomalyFilters
              filters={filters}
              onFiltersChange={setFilters}
              onClear={clearFilters}
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            {/* Results Summary */}
            {data && (
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">
                    Showing {(data.meta.page - 1) * data.meta.limit + 1}-
                    {Math.min(data.meta.page * data.meta.limit, data.meta.total)} of{' '}
                    {data.meta.total} anomalies
                  </span>
                  <span className="text-gray-400">
                    Page {data.meta.page} of {data.meta.totalPages}
                  </span>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                  <p className="text-gray-400">Loading anomalies...</p>
                </div>
              </div>
            )}

            {/* Error State */}
            {isError && (
              <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-center">
                <p className="text-red-400 mb-2">Failed to load anomalies</p>
                <p className="text-gray-400 text-sm">
                  {error instanceof Error ? error.message : 'An unknown error occurred'}
                </p>
              </div>
            )}

            {/* Anomaly List */}
            {data && !isLoading && !isError && (
              <>
                {data.data.length === 0 ? (
                  <div className="bg-gray-800 rounded-lg p-12 text-center">
                    <p className="text-gray-400 mb-2">No anomalies found</p>
                    <p className="text-gray-500 text-sm">
                      Try adjusting your filters or date range
                    </p>
                    <button
                      onClick={clearFilters}
                      className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Clear Filters
                    </button>
                  </div>
                ) : (
                  <AnomalyList anomalies={data.data} onAnomalyClick={handleAnomalyClick} />
                )}

                {/* Pagination */}
                {data.data.length > 0 && (
                  <div className="mt-6">
                    <Pagination
                      currentPage={data.meta.page}
                      totalPages={data.meta.totalPages}
                      hasNext={data.meta.hasNext}
                      hasPrev={data.meta.hasPrev}
                      onPageChange={(page) => updateFilter('page', page)}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
