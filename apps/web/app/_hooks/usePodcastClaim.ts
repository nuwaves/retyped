'use client';

import { useCallback, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useAppSelector } from '@/app/_store/hooks';
import {
  useCreatePodcastClaimMutation,
  useGetPodcastClaimsQuery,
  useVerifyPodcastClaimMutation,
} from '@/app/_store/services/podcastClaimsApi';
import {
  selectHasClaim,
  selectClaimId,
} from '@/app/_store/features/podcastClaims/podcastClaimsSlice';
import { selectIsAuthenticated } from '@/app/_store/features/auth/authSlice';

export type ClaimStatus = 'idle' | 'success' | 'exists' | 'error';

export const CLAIM_SUCCESS_MESSAGE =
  "Claim submitted. If a verification email is due, it's on its way — your claim shows as received either way.";
export const CLAIM_EXISTS_MESSAGE = "You've already claimed this show.";
const CLAIM_GENERIC_ERROR = "We couldn't submit your claim. Please try again.";

/**
 * Pull a human-readable message out of an RTK Query / DRF error.
 * DRF returns {detail}, {non_field_errors: [..]}, or {field: [..]}; the proxy
 * returns {error}; the verify endpoint returns {message}.
 */
function getErrorMessage(error: unknown): string {
  const data = (error as { data?: unknown } | null)?.data;
  if (!data || typeof data !== 'object') return CLAIM_GENERIC_ERROR;
  const record = data as Record<string, unknown>;

  for (const key of ['detail', 'message', 'error']) {
    if (typeof record[key] === 'string' && record[key]) return record[key] as string;
  }
  for (const value of Object.values(record)) {
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
  }
  return CLAIM_GENERIC_ERROR;
}

/** The (podcast, user) unique constraint rejects duplicates with a 400. */
function isDuplicateClaimError(error: unknown): boolean {
  const status = (error as { status?: unknown } | null)?.status;
  return status === 400 && /already has a claim/i.test(getErrorMessage(error));
}

/**
 * Hook for managing podcast claim interactions
 * Provides claim creation and verification submission
 * Note: Verification keys are sent via email and not stored in Redux
 *
 * The create/list endpoints do not return a claim id (the serializer exposes
 * only `podcast` and `user`), so "already claimed" is derived from the user's
 * claim list (refetched after a create) rather than from claimsMap alone.
 */
export function usePodcastClaim(podcast_id: number) {
  const router = useRouter();
  const pathname = usePathname();
  const { status: sessionStatus } = useSession();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const hasMappedClaim = useAppSelector((state) => selectHasClaim(state, podcast_id));
  const claimId = useAppSelector((state) => selectClaimId(state, podcast_id));

  const { data: claimsData } = useGetPodcastClaimsQuery(
    { limit: 100, offset: 0 },
    { skip: !isAuthenticated }
  );
  const hasListedClaim =
    isAuthenticated &&
    !!claimsData?.results?.some((claim) => claim.podcast === podcast_id);
  const hasClaim = hasMappedClaim || hasListedClaim;

  const [createClaim, { isLoading: isCreating }] =
    useCreatePodcastClaimMutation();
  const [verifyClaim, { isLoading: isVerifying }] =
    useVerifyPodcastClaimMutation();

  const [claimStatus, setClaimStatus] = useState<ClaimStatus>('idle');
  const [claimMessage, setClaimMessage] = useState<string | null>(null);

  /**
   * Create a new claim for this podcast.
   * Unauthenticated users are sent to /auth and returned to this page after login.
   * Never throws: the outcome is exposed through claimStatus / claimMessage.
   * Returns true only when a new claim was created.
   */
  const createPodcastClaim = useCallback(async () => {
    if (sessionStatus === 'loading') return false;

    if (sessionStatus === 'unauthenticated') {
      router.push(`/auth?callbackUrl=${encodeURIComponent(pathname)}`);
      return false;
    }

    if (!isAuthenticated) {
      // Session exists but the backend token has not reached the store yet
      setClaimStatus('error');
      setClaimMessage('Still signing you in. Please try again in a moment.');
      return false;
    }

    if (hasClaim) {
      setClaimStatus('exists');
      setClaimMessage(CLAIM_EXISTS_MESSAGE);
      return false;
    }

    try {
      await createClaim({ podcast: podcast_id }).unwrap();
      setClaimStatus('success');
      setClaimMessage(CLAIM_SUCCESS_MESSAGE);
      return true;
    } catch (error) {
      if (isDuplicateClaimError(error)) {
        setClaimStatus('exists');
        setClaimMessage(CLAIM_EXISTS_MESSAGE);
      } else {
        console.error('Claim creation failed:', error);
        setClaimStatus('error');
        setClaimMessage(getErrorMessage(error));
      }
      return false;
    }
  }, [sessionStatus, isAuthenticated, hasClaim, router, pathname, podcast_id, createClaim]);

  /**
   * Verify a claim using the verification key from email
   */
  const verifyPodcastClaim = useCallback(
    async (key: string) => {
      if (!isAuthenticated) {
        window.location.href = '/auth';
        return false;
      }

      try {
        const result = await verifyClaim(key).unwrap();
        return result.success;
      } catch (error) {
        console.error('Claim verification failed:', error);
        // Could add toast notification here
        throw error;
      }
    },
    [isAuthenticated, verifyClaim]
  );

  return {
    hasClaim,
    claimId,
    createPodcastClaim,
    verifyPodcastClaim,
    claimStatus,
    claimMessage,
    isSessionLoading: sessionStatus === 'loading',
    isCreating,
    isVerifying,
    isLoading: isCreating || isVerifying,
    isAuthenticated,
  };
}
