import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Terms of Service - Retyped',
  description: 'Read the Retyped terms of service — the rules and policies governing your use of our podcast discovery and AI summary platform.',
  openGraph: {
    title: 'Terms of Service - Retyped',
    description: 'Read the Retyped terms of service — the rules and policies governing your use of our podcast discovery and AI summary platform.',
    type: 'website',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'Retyped' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Terms of Service - Retyped',
    description: 'Read the Retyped terms of service — the rules and policies governing your use of our podcast discovery and AI summary platform.',
  },
};

const styles = {
  container: 'max-w-4xl mx-auto px-4 py-12',
  title: 'text-4xl font-bold mb-8',
  section: 'mb-8',
  sectionTitle: 'text-2xl font-semibold mb-4',
  paragraph: 'text-gray-700 mb-4 leading-relaxed',
};

export default function TermsPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Terms of Service</h1>

      {/*
        TODO(Billy): terms text from counsel. Do not fill this in with
        placeholder legal wording; replace the notice below with the final text.
        TODO(Billy): whether automated/AI access to transcripts is allowed, and
        the rules for quoting transcripts. Say so explicitly in the final terms.
      */}
      <section className={styles.section}>
        <p className={styles.paragraph} role="note">
          Terms of Service: being finalized. This page does not yet contain the
          binding terms. Questions in the meantime: see the{' '}
          <Link href="/contact" className="underline">contact page</Link>.
        </p>
      </section>
    </div>
  );
}
