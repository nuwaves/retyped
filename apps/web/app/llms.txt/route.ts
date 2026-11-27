import { DJANGO_BACKEND } from '@/app/_config/env';
import { buildLlmsTxt } from '@/app/_lib/llmsTxt';

// Rendered per request (the paid-API section depends on live backend state);
// the backend lookup itself is cached for 5 minutes.
export const dynamic = 'force-dynamic';

const PAID_API_PUBLIC_URL =
  process.env.PAID_API_PUBLIC_URL ||
  `${process.env.NEXT_PUBLIC_SITE_URL || 'https://retyped.xyz'}/api/v1/paid/`;

// GET /api/v1/paid/ is a 404 unless the paid API is fully enabled, so the
// paid section appears only while it is live and vanishes on rollback.
async function fetchPaidInfo(): Promise<unknown> {
  if (!DJANGO_BACKEND) return null;
  try {
    const res = await fetch(`${DJANGO_BACKEND}/api/v1/paid/`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(3000),
    });
    return res.status === 200 ? await res.json() : null;
  } catch {
    return null;
  }
}

export async function GET() {
  const body = buildLlmsTxt(await fetchPaidInfo(), PAID_API_PUBLIC_URL);
  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=300, s-maxage=300',
    },
  });
}
