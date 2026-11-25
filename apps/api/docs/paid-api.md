# Paid transcript API (x402)

> **STOP: do not launch until the transcript-rights question is settled.**
> retyped hasn't yet decided whether it may *sell* access to transcripts of
> podcasts it doesn't own. Publisher-provided public transcripts and
> approved-owner shows are the only episodes this API will serve, but "public"
> doesn't mean "licensed for resale". The API stays off (404) until
> `PAID_API_RIGHTS_CLEARED=True` (and the free-transcript gate below). Only set that after the owner (Billy) has
> settled the rights question in writing.

Decision D18 (2026-11-22): build monetization now, behind a flag, testnet only.

## Endpoints

| Path | Price | What |
|---|---|---|
| `GET /api/v1/paid/` | free | Prices, network, asset, pay-to address |
| `GET /api/v1/paid/search/?q=<words>&limit=<n>` | `PAID_API_PRICE_SEARCH_USD` (default 0.001) | Matching eligible episodes (metadata, no transcript text) |
| `GET /api/v1/paid/episodes/<slug>/transcript/` | `PAID_API_PRICE_FETCH_USD` (default 0.01) | One full transcript |

Every path returns 404 (for any HTTP method) unless `PAID_API_ENABLED`,
`PAID_API_RIGHTS_CLEARED` **and** `PAID_API_FREE_TRANSCRIPTS_CLOSED` are all
true. The third flag exists because the free `GET /api/v1/episodes/<slug>/`
currently returns full transcripts to anyone; set it only after that free path
is restricted (a separate change and decision).

## Protocol

x402 v2 over HTTP ([spec](https://github.com/coinbase/x402/blob/main/specs/x402-specification-v2.md),
[HTTP transport](https://github.com/coinbase/x402/blob/main/specs/transports-v2/http.md)),
`exact` scheme on EVM, "authorization" flow:

1. The client calls without payment and gets `402` plus a `PAYMENT-REQUIRED` header (base64 JSON: amount, asset, `payTo`, network).
2. The client retries with a `PAYMENT-SIGNATURE` header (a signed EIP-3009 USDC authorization).
3. The server checks that `accepted` equals the requirements it offered (every field, including `extra` and `maxTimeoutSeconds`), then calls the facilitator's `/verify`. It builds the response, calls `/settle`, and returns `200` plus a `PAYMENT-RESPONSE` header. Content is only sent after settlement succeeds.

Guards:
- A missing episode or a bad query is rejected **before** any charge.
- Each signed payment can be used once. The lock is keyed on what was signed (network, asset, `authorization.from`, `authorization.nonce`), not the header text, so re-encoding the header doesn't get around it. Settled payments stay locked with no expiry.
- If settlement fails clearly (the facilitator rejects it), the payment is released and the client gets a 402. If the outcome is unknown (timeout, 5xx, `settlement_pending`), the payment stays locked, no content is sent, and an error log line records the payment id, payer and path. **Those need manual reconciliation on chain; there's no automatic re-check yet.**
- A search with no results is free: it is not settled, and the payment stays unused.
- Bad numeric env values don't crash Django. They disable the paid API (503) with a logged config error.
- Rate limits are per client IP (`PAID_API_RATE_LIMIT`/min, including unpaid 402s) and per payer address (`PAID_API_PAYER_RATE_LIMIT`/min).
- A search payment can't buy a transcript, because the amounts differ. Keep the two prices different.
- Responses are `Cache-Control: no-store`, so Cloudflare won't cache paid content.

## Configuration (environment)

| Variable | Default | Notes |
|---|---|---|
| `PAID_API_ENABLED` | `False` | Feature flag |
| `PAID_API_RIGHTS_CLEARED` | `False` | Rights gate (see the top of this doc) |
| `PAID_API_FREE_TRANSCRIPTS_CLOSED` | `False` | Set only after the free episode API stops returning full transcripts |
| `PAID_API_PAY_TO` | empty | **Public** receiving address. Never put a private key anywhere in this app |
| `PAID_API_NETWORK` | `eip155:84532` | Base Sepolia (testnet) |
| `PAID_API_ALLOW_MAINNET` | `False` | Needed for any non-testnet network; real money |
| `PAID_API_ASSET` | empty (testnet: Base Sepolia USDC) | Token contract. On a non-testnet network it must be set explicitly and must not be the Base Sepolia USDC address |
| `PAID_API_ASSET_NAME` / `_VERSION` / `_DECIMALS` | empty (testnet: `USDC` / `2`) / `6` | EIP-712 domain and units. Name and version must be set explicitly on a non-testnet network |
| `PAID_API_FACILITATOR_URL` | `https://x402.org/facilitator` | Public testnet facilitator. Mainnet needs a production facilitator (e.g. Coinbase CDP, which needs an account). Must be `https` |
| `PAID_API_FACILITATOR_HEADERS` | empty | Optional static extra headers as a JSON object of strings, e.g. `{"X-Api-Key": "..."}`. A secret: environment only |
| `PAID_API_FACILITATOR_BEARER_TOKEN` | empty | Optional static bearer token, sent as `Authorization: Bearer ...`. A secret |
| `PAID_API_FACILITATOR_AUTH_HOOK` | empty | Optional dotted path to a callable `(method, url, config) -> dict` returning headers for each facilitator request (see "Facilitator authentication") |
| `PAID_API_FACILITATOR_API_KEY_ID` / `_API_KEY_SECRET` | empty | Credentials handed to the auth hook through `config.facilitator_key_id` / `.facilitator_key_secret`. Secrets: environment only, never logged |
| `PAID_API_PUBLIC_URL` (web app) | `<NEXT_PUBLIC_SITE_URL>/api/v1/paid/` | Public URL of the discovery endpoint, used for the `llms.txt` line |
| `REDIS_URL` | empty | Shared Redis for the replay lock and rate limits, e.g. `redis://redis:6379/1`. Required in production for the paid API |
| `PAID_API_PRICE_FETCH_USD` / `_SEARCH_USD` | `0.01` / `0.001` | Per request |
| `PAID_API_RATE_LIMIT` / `PAID_API_PAYER_RATE_LIMIT` | `60` / `120` | Per minute |
| `PAID_API_SEARCH_MAX_LIMIT` | `20` | Max search results |
| `PAID_API_CLIENT_IP_HEADER` | empty | **Required behind Cloudflare or any proxy**, e.g. `HTTP_CF_CONNECTING_IP`. Use a value the proxy sets itself, never the leftmost `X-Forwarded-For` entry (the client controls it); otherwise every client shares the proxy's IP and one rate-limit bucket. Only safe when the origin is reachable through Cloudflare alone (tunnel or firewall to Cloudflare IPs); otherwise it can be spoofed |
| `PAID_API_ADAPTER` | `x402` | `cloudflare` is a placeholder that fails closed |

Rate limits and the replay lock need a shared, persistent cache (`REDIS_URL`)
in production. With the local-memory cache they only hold per worker process,
and an evicted or flushed cache forgets settled payments (the facilitator's
on-chain nonce check is then the only replay guard). Moving the lock to a DB
table with a unique constraint is a possible hardening step before mainnet.

Cache selection (`settings/base.py`): when `REDIS_URL` is set, Django's built-in
`RedisCache` backend is the default cache (no extra dependency; `redis-py` is
already in `requirements.txt` for Celery), with 2 s connect and socket
timeouts. When it is unset, Django's default `LocMemCache` is used, which is
fine for dev and tests only.

**Fail-closed choice:** the API refuses to run (503) when the default cache is `LocMemCache` or
`DummyCache` and `DEBUG` is off. The refusal is per request and logged; the rest
of the site is unaffected. If Redis is configured but unreachable at request
time (rate-limit or replay-lock call raises), the request also gets 503 and no
facilitator call is made. After the lock is taken and a payment is settled,
a failing cache write is logged but the client still gets what it paid for; the
lock key stays `pending`, which blocks replays just like `settled`. Redis must not evict keys: use
`maxmemory-policy noeviction` (or a dedicated Redis DB/instance for this
cache), because an evicted lock key lets a settled payment be replayed.

Paid routes accept `GET` only; `HEAD` and other methods get 405.

Browser clients: `PAYMENT-REQUIRED` / `PAYMENT-RESPONSE` aren't in CORS
exposed headers yet; add them if browser-based payers are in scope.

## Facilitator authentication

Mainnet needs a production facilitator. Everything is configured by
environment; no credential is stored in the repo.

- `PAID_API_FACILITATOR_URL`: base URL (`/verify`, `/settle` are appended).
- Static auth: `PAID_API_FACILITATOR_BEARER_TOKEN` and/or
  `PAID_API_FACILITATOR_HEADERS` (JSON object). Sent on every facilitator
  call. Redirects are never followed, so credentials can't be forwarded.
- Per-request signed auth: set `PAID_API_FACILITATOR_AUTH_HOOK` to a dotted
  path such as `myproject.facilitator_auth.cdp_headers`. It is called as
  `hook(method, url, config)` for each request and returns a dict of headers,
  which override the static ones. Key id and secret are available as
  `config.facilitator_key_id` / `config.facilitator_key_secret` (from
  `PAID_API_FACILITATOR_API_KEY_ID` / `_API_KEY_SECRET`). A hook that cannot
  be imported fails the config check (503); a hook that raises during `/settle`
  releases the payment (nothing was sent); during `/verify` it gives a 503.

**Coinbase CDP:** its facilitator (documented as
`https://api.cdp.coinbase.com/platform/v2/x402`; confirm the URL in the CDP x402
docs) authenticates each request with a short-lived JWT signed by the CDP API
key (ES256/EdDSA, with a `uri` claim naming the method and URL). Signing needs a
JWT/crypto library, and none is in `requirements.txt` today (`PyJWT` and
`cryptography` are not listed), so **this repo does not ship a CDP signer**.
Adding one is a small, separate change: add the pinned dependency in its own PR,
write the `cdp_headers(method, url, config)` hook there, and point
`PAID_API_FACILITATOR_AUTH_HOOK` at it. Until then, either use a facilitator that
takes a static token or header, or keep the API off. The hook contract and
`manage.py paid_api_check --facilitator` (sends `GET <url>/supported` through the
same hook) are what the signer plugs into.

## Adapters

`audio_processing/paid_api/adapters.py` defines `PaymentAdapter` (`verify`,
`settle`). `X402FacilitatorAdapter` is the self-hosted path.
`CloudflareMonetizationGatewayAdapter` is a stub: Cloudflare's Monetization
Gateway is a closed US-only beta, and its origin contract isn't public. If we
get in, implement it there; the views don't change.

## Before launch (owner sign-off needed for each)
1. Transcript rights settled → `PAID_API_RIGHTS_CLEARED=True`.
2. A receiving address chosen by the owner (no wallet is created by this code).
3. A testnet trial on staging with a test client.
4. Real payments: `PAID_API_ALLOW_MAINNET=True`, mainnet USDC asset, production facilitator.
5. The free `GET /api/v1/episodes/<slug>/` stops returning full `transcript` / `script_transcript` (a separate product decision; it affects the site) → `PAID_API_FREE_TRANSCRIPTS_CLOSED=True`.
6. `PAID_API_CLIENT_IP_HEADER` set and the origin locked to Cloudflare; Redis cache in place.
7. A reconciliation routine for "settlement unknown" log lines (manual procedure below).

## Go-live runbook (Base mainnet, USDC)

Nothing in the code turns the API on. Every step below is an environment
change on the server by the owner; merging code never flips them. All
variables go in the backend's environment file (`/opt/retyped/.env` or the env
the `web` service reads; see `deploy/README.md`), then recreate `web`.

### Values

| Variable | Value | Source |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/1` (use a DB number other than the Celery broker's `/0`) | The compose Redis service on the server. Confirm the service name; this repo contains no production compose file |
| `PAID_API_PAY_TO` | `0x...` public receiving address | **Only from Billy.** Public address, never a key. Do not guess or reuse an address from chat or email |
| `PAID_API_NETWORK` | `eip155:8453` | Base mainnet (CAIP-2) |
| `PAID_API_ASSET` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Native USDC on Base, from Circle's USDC contract address list. Config refuses any other token on `eip155:8453` |
| `PAID_API_ASSET_NAME` / `_VERSION` / `_DECIMALS` | `USD Coin` / `2` / `6` | The token's EIP-712 domain; confirm by reading `name()` and `version()` on the contract (BaseScan) before launch |
| `PAID_API_FACILITATOR_URL` | production facilitator, `https://...` | Facilitator provider (e.g. CDP, see above) |
| facilitator credentials | `PAID_API_FACILITATOR_BEARER_TOKEN`, `_HEADERS`, or `_AUTH_HOOK` with `_API_KEY_ID` / `_API_KEY_SECRET` | Facilitator account, set by the owner; environment only |
| `PAID_API_CLIENT_IP_HEADER` | `HTTP_CF_CONNECTING_IP` | Only if the origin accepts traffic from Cloudflare alone |
| `PAID_API_ALLOW_MAINNET` | `True` | Owner decision: real money |
| `PAID_API_RIGHTS_CLEARED` | `True` | Owner has settled transcript rights in writing |
| `PAID_API_FREE_TRANSCRIPTS_CLOSED` | `True` | Free episode API no longer returns full transcripts |
| `PAID_API_ENABLED` | `True` | The master switch, flipped **last** |

### Flip order

1. Set `REDIS_URL`, network/asset/name/version, `PAID_API_PAY_TO`, facilitator
   URL and credentials, `PAID_API_CLIENT_IP_HEADER`, with `PAID_API_ENABLED`
   still `False`. Redis must run with `maxmemory-policy noeviction` (or be a
   dedicated instance) because an evicted lock key lets a settled payment be
   replayed.
2. Recreate `web` (and `worker`/`beat` if they share the env), then run the
   pre-flight (below). Fix anything that fails.
3. Set `PAID_API_ALLOW_MAINNET=True`, `PAID_API_RIGHTS_CLEARED=True`,
   `PAID_API_FREE_TRANSCRIPTS_CLOSED=True`, and finally `PAID_API_ENABLED=True`;
   recreate `web`.
4. Run the smoke test.

### Pre-flight checks

Inside the running `web` container, with the production env:

```bash
python manage.py paid_api_check --facilitator
```

It prints the flags, validates the config the way requests will (network,
asset, `payTo`, facilitator URL and auth, prices), round-trips a throwaway key
through the cache, warns if Redis is not `noeviction`, and sends one
`GET <facilitator>/supported` with the configured credentials. It never signs
or settles anything and never prints a secret. Exit status is non-zero on any
failure. It reports flags rather than requiring them, so it is safe to run
while the API is still off. Also check by hand:

- `payTo` printed by the command equals the address Billy sent, character for character.
- `network` is `eip155:8453` and `asset` is `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- The origin is reachable through Cloudflare only (otherwise the client-IP header can be spoofed).
- The facilitator `/supported` response lists `exact` on `eip155:8453`.

### Smoke test

No payment is needed; it only reads the 402 challenge.

```bash
curl -si https://retyped.xyz/api/v1/paid/                       # 200 JSON (use the real public URL)
curl -si "https://retyped.xyz/api/v1/paid/search/?q=rust"       # 402 + PAYMENT-REQUIRED header
curl -si "https://retyped.xyz/api/v1/paid/search/?q=rust" \
  | sed -n 's/^payment-required: //Ip' | tr -d '\r' | base64 -d | python3 -m json.tool
```

Expect: HTTP 402; in `accepts[0]`, `network` = `eip155:8453`, `asset` =
`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, `payTo` = Billy's address,
`amount` = the atomic price (`1000` for $0.001 search, `10000` for $0.01
transcript), and `extra.name`/`extra.version` = the values you
set (`USD Coin` / `2`). Anything different: roll back, then investigate.
`https://retyped.xyz/llms.txt` should now end with a "Paid API (x402)" section
(up to 5 minutes after the flip). A first real payment, if wanted, is a
separate owner-run step with a small amount.

### Rollback

Set `PAID_API_ENABLED=False` and recreate `web`. Every paid route returns 404
immediately and the `llms.txt` section disappears within 5 minutes. Settled
payments stay locked in Redis, so keep Redis data. Nothing else needs undoing.

### Reconciliation (settle timeouts)

A log line `paid API settlement unknown: payment <id> payer <addr> path <path>
reason <reason>` (logger `audio_processing.paid_api.views`), plus
`x402 settlement outcome unknown ... reconcile tx <hash> on <network>` from
the adapter, means the facilitator did not give a clear answer: the transfer may
have happened. The client got a 402 and no content, and the payment is locked
for good. For each such line, look up the payer's USDC transfer to `payTo` for
that amount around that time on BaseScan (or ask the facilitator by
transaction hash if one is logged):

- Transfer found: the client paid and got nothing. Refund it from the receiving wallet (owner action) or deliver the content by hand.
- No transfer: nothing was charged. The signed authorization stays locked here, so the client must sign a new one.

There is no automatic re-check yet. Review these lines daily for the first
weeks.
