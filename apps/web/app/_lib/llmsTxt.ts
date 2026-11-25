import { LLMS_TXT_BASE } from '@/app/_config/llms';

// What GET /api/v1/paid/ returns while the paid API is on (it is a 404 while off).
export interface PaidApiInfo {
  protocol?: unknown;
  network?: unknown;
  payTo?: unknown;
}

const NETWORK_NAMES: Record<string, string> = {
  'eip155:8453': 'Base',
  'eip155:84532': 'Base Sepolia (testnet)',
};

const EVM_ADDRESS = /^0x[0-9a-fA-F]{40}$/;

// True only for a live x402 discovery document. Anything else (404, error,
// odd shape) means "do not advertise".
export function isLivePaidApi(info: unknown): info is PaidApiInfo {
  if (!info || typeof info !== 'object') return false;
  const { protocol, network, payTo } = info as PaidApiInfo;
  return (
    protocol === 'x402' &&
    typeof network === 'string' &&
    typeof payTo === 'string' &&
    EVM_ADDRESS.test(payTo)
  );
}

// Base text, byte-identical to the old static file, plus the paid-API section
// only when `info` is a live discovery document.
export function buildLlmsTxt(info: unknown, paidApiUrl: string): string {
  if (!isLivePaidApi(info)) return LLMS_TXT_BASE;
  const network = NETWORK_NAMES[info.network as string] ?? (info.network as string);
  return (
    LLMS_TXT_BASE +
    '\n## Paid API (x402)\n' +
    `- [Paid transcript API](${paidApiUrl}): pay-per-request transcript search and full transcripts, paid in USDC on ${network} via the x402 protocol. No account needed.\n`
  );
}
