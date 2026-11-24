import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contact Us - Retyped',
  description: 'Contact the Retyped team — reach us for support, business inquiries, or feedback about our podcast discovery and AI summary platform.',
  openGraph: {
    title: 'Contact Us - Retyped',
    description: 'Contact the Retyped team — reach us for support, business inquiries, or feedback about our podcast discovery and AI summary platform.',
    type: 'website',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'Retyped' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact Us - Retyped',
    description: 'Contact the Retyped team — reach us for support, business inquiries, or feedback about our podcast discovery and AI summary platform.',
  },
};

const styles = {
  container: 'max-w-4xl mx-auto px-4 py-12',
  title: 'text-4xl font-bold mb-8',
  section: 'mb-8',
  sectionTitle: 'text-2xl font-semibold mb-4',
  paragraph: 'text-gray-700 mb-4 leading-relaxed',
};

export default function ContactPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Contact Us</h1>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Get in Touch</h2>
        {/* TODO(Billy): contact email. Replace the bracketed text below. */}
        <p className={styles.paragraph}>
          Questions, corrections or takedown requests: email [contact email to be added].
        </p>
      </section>
    </div>
  );
}
