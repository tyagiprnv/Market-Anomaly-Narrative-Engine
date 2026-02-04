/**
 * Supported crypto symbols (20 total)
 */

export const SUPPORTED_SYMBOLS = [
  'BTC-USD',
  'ETH-USD',
  'SOL-USD',
  'XRP-USD',
  'ADA-USD',
  'DOGE-USD',
  'SHIB-USD',
  'PEPE-USD',
  'AVAX-USD',
  'DOT-USD',
  'MATIC-USD',
  'LINK-USD',
  'UNI-USD',
  'LTC-USD',
  'ATOM-USD',
  'XLM-USD',
  'ALGO-USD',
  'VET-USD',
  'ICP-USD',
  'FIL-USD',
  'HBAR-USD',
] as const;

export type SupportedSymbol = typeof SUPPORTED_SYMBOLS[number];

export const SYMBOL_NAMES: Record<SupportedSymbol, string> = {
  'BTC-USD': 'Bitcoin',
  'ETH-USD': 'Ethereum',
  'SOL-USD': 'Solana',
  'XRP-USD': 'Ripple',
  'ADA-USD': 'Cardano',
  'DOGE-USD': 'Dogecoin',
  'SHIB-USD': 'Shiba Inu',
  'PEPE-USD': 'Pepe',
  'AVAX-USD': 'Avalanche',
  'DOT-USD': 'Polkadot',
  'MATIC-USD': 'Polygon',
  'LINK-USD': 'Chainlink',
  'UNI-USD': 'Uniswap',
  'LTC-USD': 'Litecoin',
  'ATOM-USD': 'Cosmos',
  'XLM-USD': 'Stellar',
  'ALGO-USD': 'Algorand',
  'VET-USD': 'VeChain',
  'ICP-USD': 'Internet Computer',
  'FIL-USD': 'Filecoin',
  'HBAR-USD': 'Hedera',
};

export function isValidSymbol(symbol: string): symbol is SupportedSymbol {
  return SUPPORTED_SYMBOLS.includes(symbol as SupportedSymbol);
}
