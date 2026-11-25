"""
Configuration for the paid transcript API, read from Django settings
(which read the environment; see settings/base.py, "Paid transcript API").
"""

import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from django.conf import settings
from django.utils.module_loading import import_string

# CAIP-2 ids of test networks. Anything else counts as mainnet and needs
# PAID_API_ALLOW_MAINNET=True.
TESTNET_NETWORKS = frozenset(
    {
        "eip155:84532",  # Base Sepolia
    }
)

# The "exact" scheme on EVM networks is the only one implemented.
SUPPORTED_SCHEME = "exact"

# Always matched with fullmatch(): "$" would accept a trailing newline.
EVM_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{40}")

# USDC on Base Sepolia (Circle testnet token): the testnet default only.
TESTNET_DEFAULT_ASSET = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
TESTNET_DEFAULT_ASSET_NAME = "USDC"
TESTNET_DEFAULT_ASSET_VERSION = "2"

# Base mainnet and its native USDC (Circle, verified at
# https://developers.circle.com/stablecoins/usdc-contract-addresses). These are
# the documented values the operator sets; nothing selects them automatically.
BASE_MAINNET_NETWORK = "eip155:8453"
BASE_MAINNET_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_MAINNET_USDC_NAME = "USD Coin"  # EIP-712 domain name on Base mainnet
BASE_MAINNET_USDC_VERSION = "2"

# Cache backends that are per process or discard everything.
UNSHARED_CACHE_BACKENDS = (
    "django.core.cache.backends.locmem.LocMemCache",
    "django.core.cache.backends.dummy.DummyCache",
)

ADAPTERS = ("x402", "cloudflare")


class PaidApiConfigError(Exception):
    """The paid API is enabled but misconfigured. Fails closed (503)."""


@dataclass(frozen=True)
class Price:
    usd: Decimal
    atomic: str  # amount in the asset's smallest unit, as x402 expects


@dataclass(frozen=True)
class PaidApiConfig:
    adapter: str
    network: str
    asset: str
    asset_name: str
    asset_version: str
    asset_decimals: int
    pay_to: str
    facilitator_url: str
    facilitator_timeout: float
    max_timeout_seconds: int
    price_fetch: Price
    price_search: Price
    rate_limit_per_minute: int
    payer_rate_limit_per_minute: int
    client_ip_header: str
    search_max_limit: int
    # Facilitator auth. Secrets stay out of repr() so a logged config is safe.
    facilitator_headers: dict = field(default_factory=dict, repr=False)
    facilitator_auth_hook: str = ""
    facilitator_key_id: str = field(default="", repr=False)
    facilitator_key_secret: str = field(default="", repr=False)


# Sanity cap on a single price, so a typo can't ask for a fortune.
MAX_PRICE_USD = Decimal("100")


def _int(name, default, low, high):
    """Integer setting in [low, high]. Settings hold raw env strings."""
    raw = getattr(settings, name, default)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise PaidApiConfigError(f"{name} must be an integer") from exc
    if not low <= value <= high:
        raise PaidApiConfigError(f"{name} must be between {low} and {high}")
    return value


def _float(name, default, low, high):
    raw = getattr(settings, name, default)
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise PaidApiConfigError(f"{name} must be a number") from exc
    if not math.isfinite(value) or not low <= value <= high:
        raise PaidApiConfigError(f"{name} must be between {low} and {high}")
    return value


def _price(value, decimals, name):
    try:
        usd = Decimal(str(value).strip())
    except (InvalidOperation, ArithmeticError) as exc:
        raise PaidApiConfigError(f"{name} is not a number") from exc
    if not usd.is_finite() or usd <= 0 or usd > MAX_PRICE_USD:
        raise PaidApiConfigError(
            f"{name} must be greater than 0 and at most {MAX_PRICE_USD}"
        )
    atomic = usd * (Decimal(10) ** decimals)
    if atomic != atomic.to_integral_value():
        raise PaidApiConfigError(
            f"{name} has more decimal places than the asset supports ({decimals})"
        )
    return Price(usd=usd, atomic=str(int(atomic)))


def _facilitator_auth():
    """Static facilitator headers (JSON and bearer token) and the optional hook path."""
    headers = {}
    raw = (getattr(settings, "PAID_API_FACILITATOR_HEADERS", "") or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise PaidApiConfigError(
                "PAID_API_FACILITATOR_HEADERS must be a JSON object"
            ) from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and k for k, v in parsed.items()
        ):
            raise PaidApiConfigError(
                "PAID_API_FACILITATOR_HEADERS must be a JSON object of strings"
            )
        headers.update(parsed)
    bearer = (getattr(settings, "PAID_API_FACILITATOR_BEARER_TOKEN", "") or "").strip()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    hook = (getattr(settings, "PAID_API_FACILITATOR_AUTH_HOOK", "") or "").strip()
    if hook:
        try:
            if not callable(import_string(hook)):
                raise PaidApiConfigError(
                    "PAID_API_FACILITATOR_AUTH_HOOK is not callable"
                )
        except PaidApiConfigError:
            raise
        except Exception as exc:  # ImportError, or an error inside the module
            raise PaidApiConfigError(
                "PAID_API_FACILITATOR_AUTH_HOOK cannot be imported"
            ) from exc
    return headers, hook


def is_enabled():
    """
    True only when the feature flag is on, the transcript-rights gate has
    been explicitly cleared, AND the free episode API no longer hands out full
    transcripts (otherwise nobody needs to pay). All three default to False.
    """
    return bool(
        getattr(settings, "PAID_API_ENABLED", False)
        and getattr(settings, "PAID_API_RIGHTS_CLEARED", False)
        and getattr(settings, "PAID_API_FREE_TRANSCRIPTS_CLOSED", False)
    )


def check_shared_cache():
    """
    The payment replay lock and rate limits live in the default cache, so it
    must be shared across workers. Outside DEBUG, per-process (LocMem) and
    no-op (Dummy) backends are refused.
    """
    if settings.DEBUG:
        return
    backend = (getattr(settings, "CACHES", {}).get("default") or {}).get("BACKEND", "")
    if backend in UNSHARED_CACHE_BACKENDS:
        raise PaidApiConfigError(
            "the default cache must be shared across workers (set REDIS_URL); "
            f"{backend.rsplit('.', 1)[-1]} is not safe for payment replay locks"
        )


def get_config():
    """Build and validate the config. Raises PaidApiConfigError."""
    s = settings
    check_shared_cache()
    adapter = getattr(s, "PAID_API_ADAPTER", "x402")
    if adapter not in ADAPTERS:
        raise PaidApiConfigError(f"PAID_API_ADAPTER must be one of {ADAPTERS}")

    network = str(getattr(s, "PAID_API_NETWORK", "eip155:84532") or "")
    if not network.startswith("eip155:"):
        raise PaidApiConfigError("only EVM (eip155:*) networks are supported")
    if network not in TESTNET_NETWORKS and not getattr(
        s, "PAID_API_ALLOW_MAINNET", False
    ):
        raise PaidApiConfigError(
            f"{network} is not a known testnet; set PAID_API_ALLOW_MAINNET=True "
            "only after the owner approves real payments"
        )

    pay_to = getattr(s, "PAID_API_PAY_TO", "")
    if not EVM_ADDRESS_RE.fullmatch(pay_to or ""):
        raise PaidApiConfigError("PAID_API_PAY_TO must be a 0x-prefixed EVM address")

    is_testnet = network in TESTNET_NETWORKS
    asset = getattr(s, "PAID_API_ASSET", "") or ""
    asset_name = getattr(s, "PAID_API_ASSET_NAME", "") or ""
    asset_version = str(getattr(s, "PAID_API_ASSET_VERSION", "") or "")
    if is_testnet:
        asset = asset or TESTNET_DEFAULT_ASSET
        asset_name = asset_name or TESTNET_DEFAULT_ASSET_NAME
        asset_version = asset_version or TESTNET_DEFAULT_ASSET_VERSION
    else:
        # Never inherit testnet token defaults on a network with real money.
        if not asset or asset.lower() == TESTNET_DEFAULT_ASSET.lower():
            raise PaidApiConfigError(
                "PAID_API_ASSET must be set explicitly to the network's token "
                "(not the Base Sepolia USDC default) on a non-testnet network"
            )
        if not asset_name or not asset_version:
            raise PaidApiConfigError(
                "PAID_API_ASSET_NAME and PAID_API_ASSET_VERSION must be set "
                "explicitly on a non-testnet network"
            )
    if not EVM_ADDRESS_RE.fullmatch(asset):
        raise PaidApiConfigError("PAID_API_ASSET must be a 0x-prefixed token address")
    if network == BASE_MAINNET_NETWORK and asset.lower() != BASE_MAINNET_USDC.lower():
        # Catches a pasted wrong or look-alike token before real money moves.
        raise PaidApiConfigError(
            f"on {BASE_MAINNET_NETWORK} (Base) PAID_API_ASSET must be Circle's "
            f"USDC {BASE_MAINNET_USDC}"
        )

    decimals = _int("PAID_API_ASSET_DECIMALS", 6, 0, 18)

    facilitator_url = (getattr(s, "PAID_API_FACILITATOR_URL", "") or "").rstrip("/")
    if adapter == "x402" and not facilitator_url.startswith("https://"):
        raise PaidApiConfigError("PAID_API_FACILITATOR_URL must be an https URL")
    if adapter == "x402":
        parsed = urlparse(facilitator_url)
        if parsed.username or parsed.password or parsed.query:
            # Credentials belong in headers; URLs end up in error logs.
            raise PaidApiConfigError(
                "PAID_API_FACILITATOR_URL must not contain credentials or a query"
            )

    facilitator_headers, facilitator_hook = _facilitator_auth()

    return PaidApiConfig(
        adapter=adapter,
        network=network,
        asset=asset,
        asset_name=asset_name,
        asset_version=asset_version,
        asset_decimals=decimals,
        pay_to=pay_to,
        facilitator_url=facilitator_url,
        facilitator_timeout=_float("PAID_API_FACILITATOR_TIMEOUT", 15, 1, 120),
        max_timeout_seconds=_int("PAID_API_MAX_TIMEOUT_SECONDS", 60, 10, 3600),
        price_fetch=_price(
            getattr(s, "PAID_API_PRICE_FETCH_USD", "0.01"),
            decimals,
            "PAID_API_PRICE_FETCH_USD",
        ),
        price_search=_price(
            getattr(s, "PAID_API_PRICE_SEARCH_USD", "0.001"),
            decimals,
            "PAID_API_PRICE_SEARCH_USD",
        ),
        rate_limit_per_minute=_int("PAID_API_RATE_LIMIT", 60, 1, 100_000),
        payer_rate_limit_per_minute=_int("PAID_API_PAYER_RATE_LIMIT", 120, 1, 100_000),
        client_ip_header=getattr(s, "PAID_API_CLIENT_IP_HEADER", "") or "",
        search_max_limit=_int("PAID_API_SEARCH_MAX_LIMIT", 20, 1, 100),
        facilitator_headers=facilitator_headers,
        facilitator_auth_hook=facilitator_hook,
        facilitator_key_id=getattr(s, "PAID_API_FACILITATOR_API_KEY_ID", "") or "",
        facilitator_key_secret=getattr(s, "PAID_API_FACILITATOR_API_KEY_SECRET", "")
        or "",
    )
