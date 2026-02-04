/**
 * Transforms Prisma price models to API DTOs
 */

import type { prices } from '@prisma/client';
import type { PriceDataDTO } from '@mane/shared';

/**
 * Transform Prisma price to PriceDataDTO
 */
export function toPriceDataDTO(price: prices): PriceDataDTO {
  return {
    timestamp: price.timestamp.toISOString(),
    symbol: price.symbol,
    price: price.price,
    volume: price.volume_24h,
  };
}
