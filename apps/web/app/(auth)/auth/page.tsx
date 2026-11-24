import { Metadata } from 'next';
import { Suspense } from 'react';
import AuthLayout from '@/app/_components/auth/AuthLayout';
import AuthHero from '@/app/_components/auth/AuthHero';
import AuthCard from '@/app/_components/auth/AuthCard';


export const metadata: Metadata = {
  title: 'Sign In | Retyped',
  robots: { index: false, follow: true },
};

export default function LoginPage() {
  return (
    <AuthLayout
      headerTitle="Discover amazing podcasts"
      headerDescription="Build your personal podcast library with bookmarks, follows, and more."
      hero={
        <AuthHero
          title="Discover amazing podcasts"
          description="Transcripts are free to read without an account. Sign in to build your personal library of bookmarked episodes and followed podcasts, and request transcripts for episodes that don't have one yet."
        />
      }
      authCard={
        <Suspense fallback={<div>Loading...</div>}>
          <AuthCard mode="login" />
        </Suspense>
      }
    />
  );
}
