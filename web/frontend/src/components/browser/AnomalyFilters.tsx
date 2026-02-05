/**
 * Filter component for anomaly browser
 */

import { useState } from 'react';
import { AnomalyFilters as Filters } from '@mane/shared/types/api';
import { AnomalyType, ValidationStatus } from '@mane/shared/types/enums';
import { SUPPORTED_SYMBOLS, SYMBOL_NAMES } from '@mane/shared/constants/symbols';
import { saveFilters, loadFilters, hasSavedFilters, clearStoredFilters } from '../../utils/filterStorage';
import { showSuccess, showInfo } from '../common';

interface AnomalyFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onClear: () => void;
}

export function AnomalyFilters({ filters, onFiltersChange, onClear }: AnomalyFiltersProps) {
  const [showSymbols, setShowSymbols] = useState(false);

  // Toggle symbol selection
  const toggleSymbol = (symbol: string) => {
    const symbols = filters.symbols || [];
    const updated = symbols.includes(symbol)
      ? symbols.filter((s) => s !== symbol)
      : [...symbols, symbol];
    onFiltersChange({ ...filters, symbols: updated.length > 0 ? updated : undefined });
  };

  // Toggle all symbols
  const toggleAllSymbols = () => {
    if (filters.symbols?.length === SUPPORTED_SYMBOLS.length) {
      onFiltersChange({ ...filters, symbols: undefined });
    } else {
      onFiltersChange({ ...filters, symbols: [...SUPPORTED_SYMBOLS] });
    }
  };

  // Toggle anomaly type
  const toggleType = (type: AnomalyType) => {
    const types = filters.types || [];
    const updated = types.includes(type)
      ? types.filter((t) => t !== type)
      : [...types, type];
    onFiltersChange({ ...filters, types: updated.length > 0 ? updated : undefined });
  };

  // Toggle validation status
  const toggleValidation = (status: ValidationStatus) => {
    const statuses = filters.validationStatus || [];
    const updated = statuses.includes(status)
      ? statuses.filter((s) => s !== status)
      : [...statuses, status];
    onFiltersChange({ ...filters, validationStatus: updated.length > 0 ? updated : undefined });
  };

  // Save current filters
  const handleSaveFilters = () => {
    saveFilters(filters);
    showSuccess('Filters saved successfully!');
  };

  // Load saved filters
  const handleLoadFilters = () => {
    const saved = loadFilters();
    if (saved) {
      onFiltersChange({ ...filters, ...saved, page: 1 });
      showInfo('Filters loaded from saved preset');
    }
  };

  // Clear all (including stored)
  const handleClearAll = () => {
    clearStoredFilters();
    onClear();
    showInfo('All filters cleared');
  };

  const hasActiveFilters =
    filters.symbols?.length ||
    filters.types?.length ||
    filters.validationStatus?.length ||
    filters.startDate ||
    filters.endDate;

  return (
    <div className="bg-gray-800 rounded-lg p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-100">Filters</h2>
        <div className="flex gap-2">
          {hasSavedFilters() && (
            <button
              onClick={handleLoadFilters}
              className="px-3 py-1 text-sm bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors"
            >
              Load Saved
            </button>
          )}
          {hasActiveFilters && (
            <>
              <button
                onClick={handleSaveFilters}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Save Filters
              </button>
              <button
                onClick={handleClearAll}
                className="px-3 py-1 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Clear All
              </button>
            </>
          )}
        </div>
      </div>

      {/* Symbols */}
      <div>
        <button
          onClick={() => setShowSymbols(!showSymbols)}
          className="flex items-center justify-between w-full text-left mb-2"
        >
          <span className="text-sm font-medium text-gray-300">
            Symbols {filters.symbols?.length ? `(${filters.symbols.length})` : ''}
          </span>
          <span className="text-gray-500">{showSymbols ? '▼' : '▶'}</span>
        </button>

        {showSymbols && (
          <div className="space-y-2">
            <button
              onClick={toggleAllSymbols}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              {filters.symbols?.length === SUPPORTED_SYMBOLS.length ? 'Clear All' : 'Select All'}
            </button>
            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
              {SUPPORTED_SYMBOLS.map((symbol) => (
                <label key={symbol} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.symbols?.includes(symbol) || false}
                    onChange={() => toggleSymbol(symbol)}
                    className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
                  />
                  <span className="text-gray-300">{SYMBOL_NAMES[symbol]}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Date Range */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Date Range</label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Start Date</label>
            <input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) =>
                onFiltersChange({ ...filters, startDate: e.target.value || undefined })
              }
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">End Date</label>
            <input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) =>
                onFiltersChange({ ...filters, endDate: e.target.value || undefined })
              }
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Anomaly Type */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Anomaly Type {filters.types?.length ? `(${filters.types.length})` : ''}
        </label>
        <div className="space-y-2">
          {Object.values(AnomalyType).map((type) => (
            <label key={type} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={filters.types?.includes(type) || false}
                onChange={() => toggleType(type)}
                className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <span className="text-gray-300">{type.replace(/_/g, ' ')}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Validation Status */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Validation Status {filters.validationStatus?.length ? `(${filters.validationStatus.length})` : ''}
        </label>
        <div className="space-y-2">
          {Object.values(ValidationStatus).map((status) => (
            <label key={status} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={filters.validationStatus?.includes(status) || false}
                onChange={() => toggleValidation(status)}
                className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <span className="text-gray-300">{status.replace(/_/g, ' ')}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
