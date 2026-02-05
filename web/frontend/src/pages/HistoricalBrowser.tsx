/**
 * Historical anomaly browser page with filtering and pagination
 */
import { useNavigate } from 'react-router-dom';
import { useAnomalies } from '../api/queries/anomalies';
import { useFilterState } from '../utils/urlState';
import { AnomalyFilters } from '../components/browser';
import { AnomalyList } from '../components/dashboard';
import { Pagination, ListSkeleton, AnomalyCardSkeleton, NoAnomaliesFound, ErrorState } from '../components/common';
import { AppLayout } from '../components/layout/AppLayout';
import { AnomalyDTO } from '@mane/shared/types/api';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

export function HistoricalBrowser() {
  useDocumentTitle('Historical Anomalies');
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
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-100 mb-2">Historical Anomalies</h1>
          <p className="text-sm sm:text-base text-gray-400">
            Browse and filter all detected price anomalies across all symbols and timeframes.
          </p>
        </div>

        {/* Layout: Filters sidebar + Content */}
        <div className="flex flex-col lg:grid lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            <AnomalyFilters
              filters={filters}
              onFiltersChange={setFilters}
              onClear={clearFilters}
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-4 sm:space-y-6">
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
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ListSkeleton count={6} ItemSkeleton={AnomalyCardSkeleton} />
              </div>
            )}

            {/* Error State */}
            {isError && (
              <div className="bg-gray-800 rounded-lg p-6">
                <ErrorState
                  message={error instanceof Error ? error.message : 'Failed to load anomalies. Please try again.'}
                />
              </div>
            )}

            {/* Anomaly List */}
            {data && !isLoading && !isError && (
              <>
                <AnomalyList
                  anomalies={data.data}
                  onAnomalyClick={handleAnomalyClick}
                  emptyState={<NoAnomaliesFound onClearFilters={clearFilters} />}
                />

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
