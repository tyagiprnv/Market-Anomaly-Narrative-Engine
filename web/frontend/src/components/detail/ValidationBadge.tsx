/**
 * Badge component for displaying validation status
 */

import { ValidationStatus } from '@mane/shared/types/enums';
import { getValidationStatusColor } from '../../utils/formatters';

interface ValidationBadgeProps {
  status: ValidationStatus;
  reason?: string | null;
}

export function ValidationBadge({ status, reason }: ValidationBadgeProps) {
  const color = getValidationStatusColor(status);

  const bgColorMap = {
    success: 'bg-green-100 text-green-800 border-green-200',
    danger: 'bg-red-100 text-red-800 border-red-200',
    neutral: 'bg-gray-100 text-gray-800 border-gray-200',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    info: 'bg-blue-100 text-blue-800 border-blue-200',
  };

  const iconMap = {
    success: '✓',
    danger: '✗',
    neutral: '?',
    warning: '!',
    info: 'ℹ',
  };

  const labelMap: Record<ValidationStatus, string> = {
    [ValidationStatus.VALID]: 'Valid',
    [ValidationStatus.INVALID]: 'Invalid',
    [ValidationStatus.PENDING]: 'Pending',
    [ValidationStatus.NOT_GENERATED]: 'Not Generated',
  };

  return (
    <div className="inline-flex items-center gap-2">
      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${bgColorMap[color]}`}>
        <span>{iconMap[color]}</span>
        <span>{labelMap[status]}</span>
      </span>
      {reason && (
        <span className="text-sm text-gray-600 italic">
          {reason}
        </span>
      )}
    </div>
  );
}
