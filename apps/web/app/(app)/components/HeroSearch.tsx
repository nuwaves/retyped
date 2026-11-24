'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/app/_components/common/Button';

const styles = {
  container: "flex items-center justify-center px-4 py-12 lg:py-20",
  wrapper: "max-w-4xl w-full text-center",
  title: "text-xl sm:text-2xl lg:text-[32px] font-bold leading-[125%] tracking-normal text-center align-middle lining-nums proportional-nums mb-6 px-4 lg:px-8 text-slate-900",
  description: "text-sm lg:text-base font-normal leading-6 tracking-normal text-center text-gray-600 lining-nums proportional-nums mb-8 lg:mb-12 px-4 lg:px-8",
  question: "text-xl lg:text-2xl font-semibold text-slate-900 mt-10 lg:mt-14 mb-3 px-4 lg:px-8",
  answer: "text-sm lg:text-base font-normal leading-6 text-gray-600 px-4 lg:px-8 max-w-2xl mx-auto",
  searchContainer: "w-full px-4 lg:px-0",
  inputWrapper: "flex gap-2 max-w-[732px] mx-auto items-center",
  input: "flex-1 min-h-[45px] h-[45px] md:min-h-[40px] md:h-[40px] px-4 text-sm lg:text-[16px] font-normal leading-[24px] tracking-normal border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent focus:bg-white transition-colors duration-300 ease-out lining-nums proportional-nums placeholder:text-sm lg:placeholder:text-base",
  inputShadow: "0px 2px 6px 0px #00000008",
  button: "hidden min-[380px]:block !w-auto lg:!w-[79px] !px-3 lg:!px-0 !py-0 !h-[45px] md:!h-[40px]"
};

export default function HeroSearch() {
  const [searchQuery, setSearchQuery] = useState('');
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        {/*
          TODO(Billy): add the indexed-episode count with an "as of <month year>"
          date, e.g. "...what was said in N episodes (as of Month YYYY)". Until
          then the sentence carries no number. Keep this the page's only h1.
        */}
        <h1 className={styles.title}>
          Retyped is a podcast transcript and summary site that lets you read and search what was said in podcast episodes.
        </h1>

        <p className={styles.description}>
          Find shows you love. Build your personal media library.
        </p>

        <form onSubmit={handleSearch} className={styles.searchContainer}>
          <div className={styles.inputWrapper}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search people, shows, topics"
              className={styles.input}
              style={{ boxShadow: styles.inputShadow }}
            />
            <Button
              type="submit"
              variant="secondary"
              size="md"
              className={styles.button}
            >
              Search
            </Button>
          </div>
        </form>

        {/*
          TODO(Billy): the answer below is limited to what the code shows
          (AI summaries and transcripts exist for indexed episodes, and search
          works over them; transcripts are free to read, no account needed).
          Supply, if wanted: whether every indexed episode has a transcript, an accuracy statement, and any
          wording about playing audio.
        */}
        <h2 className={styles.question}>
          Where can I read a podcast transcript instead of listening?
        </h2>
        <p className={styles.answer}>
          Retyped has AI summaries and transcripts for indexed podcast episodes, free to read and searchable by what was said.
        </p>
      </div>
    </div>
  );
}