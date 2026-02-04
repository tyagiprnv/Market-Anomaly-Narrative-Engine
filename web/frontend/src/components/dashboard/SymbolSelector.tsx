/**
 * Multi-select dropdown for filtering by crypto symbols
 */

import { useState, useRef, useEffect } from 'react';
import { SUPPORTED_SYMBOLS, SYMBOL_NAMES, type SupportedSymbol } from '@mane/shared/constants/symbols';
import { formatSymbol } from '../../utils/formatters';

interface SymbolSelectorProps {
  selected: string[];
  onChange: (symbols: string[]) => void;
  className?: string;
}

export function SymbolSelector({ selected, onChange, className = '' }: SymbolSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleSymbol = (symbol: string) => {
    if (selected.includes(symbol)) {
      onChange(selected.filter((s) => s !== symbol));
    } else {
      onChange([...selected, symbol]);
    }
  };

  const selectAll = () => {
    onChange([...SUPPORTED_SYMBOLS]);
  };

  const clearAll = () => {
    onChange([]);
  };

  const displayText =
    selected.length === 0
      ? 'All Symbols'
      : selected.length === SUPPORTED_SYMBOLS.length
      ? 'All Symbols'
      : selected.length === 1
      ? formatSymbol(selected[0])
      : `${selected.length} symbols`;

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-secondary w-full flex items-center justify-between gap-2"
      >
        <span className="truncate">{displayText}</span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-96 overflow-y-auto">
          {/* Header with Select All / Clear All */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-2 flex gap-2">
            <button
              type="button"
              onClick={selectAll}
              className="flex-1 px-3 py-1 text-xs font-medium text-primary-700 hover:bg-primary-50 rounded"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={clearAll}
              className="flex-1 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded"
            >
              Clear All
            </button>
          </div>

          {/* Symbol list */}
          <div className="p-2">
            {SUPPORTED_SYMBOLS.map((symbol) => (
              <label
                key={symbol}
                className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(symbol)}
                  onChange={() => toggleSymbol(symbol)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <div className="flex-1 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {formatSymbol(symbol)}
                  </span>
                  <span className="text-xs text-gray-500">{SYMBOL_NAMES[symbol as SupportedSymbol]}</span>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
