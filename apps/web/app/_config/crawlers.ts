// Crawler policy for robots.txt (decision D17, 2026-11-22):
// allow search crawlers, block bulk AI-training crawlers until a paid route
// (Cloudflare Pay Per Use / pay per crawl, or the paid transcript API) is live.
//
// Sources for which user-agent does what:
// - Operator docs:
//   OpenAI      https://platform.openai.com/docs/bots
//   Anthropic   https://support.anthropic.com/en/articles/8896518
//   Google      https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
//   Perplexity  https://docs.perplexity.ai/guides/bots
//   Apple       https://support.apple.com/en-us/119829
//   Meta        https://developers.facebook.com/docs/sharing/webmasters/web-crawlers
//   Common Crawl https://commoncrawl.org/ccbot
//   Mistral     https://docs.mistral.ai/robots/
// - Community list: https://github.com/ai-robots-txt/ai.robots.txt
//   (robots.json at commit eba7fddcfdac4ab9c079322464422c5c41af8f44, 2026-11-22),
//   used only for bots whose stated function is model training or dataset building.
//
// Matches the Terms of Service (app/(company)/terms): AI search and answer
// engines may index and cite retyped pages with a link back; no AI training
// without written permission.
//
// Not listed here on purpose (they fall under the `*` group and stay allowed):
// - general crawlers with mixed uses (Amazonbot, GoogleOther). Revisit with AI
//   Crawl Control data (D16).
// - user-initiated fetchers that load one page because a person asked an AI
//   assistant: Meta-ExternalFetcher, MistralAI-User, DuckAssistBot (the last
//   feeds DuckDuckGo answers). Same reasoning as ChatGPT-User / Claude-User.
// - omgilibot: legacy Webz.io token; ai.robots.txt says the `omgili` agent is
//   the one still used, so only `omgili` is listed.
//
// Entries marked "community-listed" come from ai.robots.txt robots.json only
// and are not documented by the vendor.
//
// robots.txt is advisory. Bots that ignore it have to be blocked at Cloudflare.

// Paths no crawler should fetch. Same list as the `*` group.
export const PRIVATE_PATHS = ['/api/', '/auth/'];

// Search and answer-engine crawlers: allowed, so retyped stays in search
// results and AI answers (SEO / AEO).
export const SEARCH_CRAWLERS = [
  'Googlebot', // Google Search
  'Bingbot', // Bing (also feeds Copilot and DuckDuckGo results)
  'DuckDuckBot',
  'Applebot', // Siri / Spotlight search; training is controlled by Applebot-Extended
  'OAI-SearchBot', // ChatGPT search; not used for training (OpenAI docs)
  'Claude-SearchBot', // Claude search quality; not training (Anthropic docs)
  'PerplexityBot', // Perplexity search index; not training (Perplexity docs)
  // User-initiated fetchers: fetch one page because a person asked, to answer
  // them with a citation. Named explicitly so the policy is visible in the file.
  'ChatGPT-User',
  'Claude-User',
  'Perplexity-User',
];

// Bulk training / dataset crawlers: blocked from the whole site.
export const TRAINING_CRAWLERS = [
  'GPTBot', // OpenAI model training
  'ClaudeBot', // Anthropic model training
  'anthropic-ai', // older Anthropic training token
  'Google-Extended', // Gemini / Vertex AI training token; does not affect Google Search
  'Applebot-Extended', // Apple Intelligence training token; does not affect Applebot search
  'CCBot', // Common Crawl open dataset, widely used for LLM training
  'Bytespider', // ByteDance LLM training
  'TikTokSpider', // ByteDance LLM training
  'meta-externalagent', // Meta model training
  'FacebookBot', // Meta speech/language-model data; link previews use facebookexternalhit (allowed)
  'cohere-training-data-crawler', // Cohere training data
  'MistralAI-Training', // Mistral training (documented at docs.mistral.ai/robots)
  'DeepSeekBot', // DeepSeek training; community-listed (ai.robots.txt), not vendor-documented
  'AI2Bot', // Ai2 open-model training
  'Ai2Bot-Dolma', // Ai2 Dolma dataset
  'Hunyuan', // Tencent training crawler; community-listed (ai.robots.txt), not vendor-documented
  'MoonshotBot', // Moonshot / Kimi training crawler; community-listed (ai.robots.txt), not vendor-documented
  'PanguBot', // Huawei data scraper
  'Timpibot', // training data for LLMs
  'YandexAdditional', // YandexGPT
  'YandexAdditionalBot', // YandexGPT
  'img2dataset', // dataset builder
  'Cotoyogi', // LLM scraper
  'ICC-Crawler', // NICT AI training
  'Diffbot', // knowledge-graph data provider; community-listed (ai.robots.txt), not vendor-documented
  'omgili', // Webz.io; data sold, incl. for LLM training; community-listed (ai.robots.txt), not vendor-documented
  'Webzio-Extended', // Webz.io AI data scraper; community-listed (ai.robots.txt), not vendor-documented
  'ImagesiftBot', // ImageSift image scraper; community-listed (ai.robots.txt), not vendor-documented
];
