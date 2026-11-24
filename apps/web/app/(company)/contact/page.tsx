import { Metadata } from 'next';
import Link from 'next/link';

const description =
  'Contact Retyped: support, podcast claims, transcript corrections and removal requests.';

export const metadata: Metadata = {
  title: 'Contact Us - Retyped',
  description,
  alternates: { canonical: '/contact' },
  openGraph: {
    title: 'Contact Us - Retyped',
    description,
    type: 'website',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'Retyped' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact Us - Retyped',
    description,
  },
};

const styles = {
  container: 'max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16',
  title: 'text-3xl font-bold mb-3 text-gray-900',
  lead: 'text-gray-600 mb-12 leading-relaxed text-base',
  section: 'mb-12',
  sectionTitle: 'text-xl font-bold mb-4 text-gray-900',
  paragraph: 'text-gray-600 mb-4 leading-relaxed text-base',
  link: 'text-gray-900 underline hover:no-underline',
};

export default function ContactPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Contact Us</h1>
      <p className={styles.lead}>
        Email us at <a href="mailto:support@nuwaves.xyz" className={styles.link}>support@nuwaves.xyz</a>{' '}
        and we&apos;ll get back to you.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Podcast owners</h2>
        <p className={styles.paragraph}>
          If you own or represent a podcast, you can claim it from the show page on retyped. To ask
          for a transcript or summary to be corrected or removed, email us the show or episode link
          and how you are connected to the podcast.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Everything else</h2>
        <p className={styles.paragraph}>
          Questions about how the site works, bugs, or permission for anything covered by the{' '}
          <Link href="/terms" className={styles.link}>Terms of Service</Link> (including AI access
          and quoting): the same address, <a href="mailto:support@nuwaves.xyz" className={styles.link}>support@nuwaves.xyz</a>.
        </p>
      </section>
    </div>
  );
}
