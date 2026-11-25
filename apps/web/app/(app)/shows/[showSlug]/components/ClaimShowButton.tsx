'use client';

import Button from '@/app/_components/common/Button';
import { usePodcastClaim } from '@/app/_hooks/usePodcastClaim';

interface ClaimShowButtonProps {
  podcastId: number;
  fullWidth?: boolean;
}

const styles = {
  wrapper: "flex flex-col gap-2",
  button: "disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:border-gray-300",
  message: "text-xs font-normal leading-4",
  messageOk: "text-neutral-500",
  messageError: "text-red-600",
};

export default function ClaimShowButton({ podcastId, fullWidth = false }: ClaimShowButtonProps) {
  const {
    hasClaim,
    claimStatus,
    claimMessage,
    createPodcastClaim,
    isCreating,
    isSessionLoading,
  } = usePodcastClaim(podcastId);

  const isPending = hasClaim || claimStatus === 'success' || claimStatus === 'exists';

  const label = isCreating ? 'Claiming…' : isPending ? 'Claim pending' : 'Claim Show';

  return (
    <div className={styles.wrapper}>
      <Button
        onClick={createPodcastClaim}
        disabled={isCreating || isPending || isSessionLoading}
        variant="outline"
        size="md"
        fullWidth={fullWidth}
        className={styles.button}
      >
        {label}
      </Button>
      {claimMessage && (
        <p
          role={claimStatus === 'error' ? 'alert' : 'status'}
          className={`${styles.message} ${claimStatus === 'error' ? styles.messageError : styles.messageOk}`}
        >
          {claimMessage}
        </p>
      )}
    </div>
  );
}
