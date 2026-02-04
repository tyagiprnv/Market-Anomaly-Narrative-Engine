/**
 * Component for displaying the narrative with metadata
 */

import { NarrativeDTO } from '@mane/shared/types/database';
import { ValidationBadge } from './ValidationBadge';
import { formatDate, formatPercent } from '../../utils/formatters';

interface NarrativeDisplayProps {
  narrative: NarrativeDTO;
}

export function NarrativeDisplay({ narrative }: NarrativeDisplayProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
      <div className="flex items-start justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">AI-Generated Narrative</h2>
        <ValidationBadge
          status={narrative.validationStatus}
          reason={narrative.validationReason}
        />
      </div>

      <div className="mb-4">
        <p className="text-gray-800 text-lg leading-relaxed">
          {narrative.narrative}
        </p>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <div>
            <span className="font-medium">Confidence:</span>{' '}
            <span className="font-semibold text-gray-900">
              {formatPercent(narrative.confidence * 100)}
            </span>
          </div>
          <div>
            <span className="font-medium">Generated:</span>{' '}
            <span>{formatDate(narrative.createdAt)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
