import type { ReactNode } from 'react';

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabNavigationProps {
  tabs: Tab[];
}

const styles = {
  container: "w-full",
  nav: "inline-flex max-w-full overflow-x-auto bg-gray-100/50 rounded-lg p-1.5 mb-6 gap-1",
  link: "px-4 sm:px-6 py-2 font-medium text-sm whitespace-nowrap rounded-md transition-colors duration-200 text-gray-600 hover:text-gray-900 hover:bg-white",
  sections: "flex flex-col gap-6",
  // Leaves room for the fixed navbar when a jump link scrolls to a section.
  section: "scroll-mt-20",
};

// Every section is rendered in the normal flow of the initial HTML (no
// `hidden` panels, no client-only state), so summary, show notes and
// transcript are visible to readers and to crawlers that don't run scripts.
// The links jump to a section and work without JavaScript.
export default function TabNavigation({ tabs }: TabNavigationProps) {
  return (
    <div className={styles.container}>
      <nav aria-label="Episode content" className={styles.nav}>
        {tabs.map((tab) => (
          <a key={tab.id} href={`#${tab.id}`} className={styles.link}>
            {tab.label}
          </a>
        ))}
      </nav>

      <div className={styles.sections}>
        {tabs.map((tab) => (
          <section key={tab.id} id={tab.id} className={styles.section}>
            {tab.content}
          </section>
        ))}
      </div>
    </div>
  );
}
