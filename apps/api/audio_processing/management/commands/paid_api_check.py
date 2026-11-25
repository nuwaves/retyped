"""
Pre-flight for the paid transcript API (docs/paid-api.md, "Go-live runbook").

Read-only: validates the environment the way the API will at request time and
round-trips a throwaway key through the cache. It never signs, pays or
settles anything. Run it with the production environment before flipping any
flag (the flags themselves may still be off; they are reported, not required).

    python manage.py paid_api_check [--facilitator]

--facilitator also sends one GET <facilitator>/supported with the configured
credentials (the only network call). Exit status is 1 if any check fails.
"""

import uuid
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from ...paid_api import config as paid_config
from ...paid_api.adapters import X402FacilitatorAdapter


class Command(BaseCommand):
    help = (
        "Check paid API configuration, shared cache and (optionally) the facilitator."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--facilitator",
            action="store_true",
            help="Also GET <facilitator>/supported with the configured credentials.",
        )

    def handle(self, *args, **options):
        failures = []

        def ok(msg):
            self.stdout.write(self.style.SUCCESS(f"ok    {msg}"))

        def warn(msg):
            self.stdout.write(self.style.WARNING(f"warn  {msg}"))

        def fail(msg):
            failures.append(msg)
            self.stdout.write(self.style.ERROR(f"FAIL  {msg}"))

        flags = {
            name: bool(getattr(settings, name, False))
            for name in (
                "PAID_API_ENABLED",
                "PAID_API_RIGHTS_CLEARED",
                "PAID_API_FREE_TRANSCRIPTS_CLOSED",
                "PAID_API_ALLOW_MAINNET",
            )
        }
        for name, value in flags.items():
            self.stdout.write(f"      {name}={value}")
        self.stdout.write(f"      serving: {paid_config.is_enabled()}")

        config = None
        try:
            config = paid_config.get_config()
            ok(
                f"config valid: network={config.network} asset={config.asset} "
                f"payTo={config.pay_to}"
            )
            self.stdout.write(
                f"      price fetch=${config.price_fetch.usd} "
                f"search=${config.price_search.usd}"
            )
            if config.network not in paid_config.TESTNET_NETWORKS:
                if flags["PAID_API_ALLOW_MAINNET"]:
                    warn("MAINNET: real money. Check payTo against the owner's note.")
                else:
                    fail("mainnet network without PAID_API_ALLOW_MAINNET")
            host = urlparse(config.facilitator_url).netloc
            has_auth = bool(config.facilitator_headers or config.facilitator_auth_hook)
            self.stdout.write(
                f"      facilitator={host} auth={'configured' if has_auth else 'none'}"
            )
            if not config.client_ip_header:
                warn(
                    "PAID_API_CLIENT_IP_HEADER is empty: behind a proxy all clients "
                    "share one rate-limit bucket"
                )
        except paid_config.PaidApiConfigError as exc:
            fail(f"config: {exc}")

        backend = (settings.CACHES.get("default") or {}).get("BACKEND", "")
        if backend in paid_config.UNSHARED_CACHE_BACKENDS and not settings.DEBUG:
            fail(
                f"cache backend {backend.rsplit('.', 1)[-1]} is not shared (set REDIS_URL)"
            )
        else:
            key = f"paid_api:check:{uuid.uuid4().hex}"
            try:
                if not cache.add(key, "x", timeout=30):
                    raise RuntimeError("cache.add returned False for a new key")
                if cache.add(key, "y", timeout=30):
                    raise RuntimeError("second cache.add on the same key succeeded")
                cache.delete(key)
                ok(f"cache round-trip ({backend.rsplit('.', 1)[-1]})")
            except Exception as exc:
                fail(f"cache round-trip failed: {exc}")
            self._check_eviction(backend, ok, warn)

        if options["facilitator"] and config is not None:
            url = f"{config.facilitator_url}/supported"
            try:
                headers = X402FacilitatorAdapter(config)._headers(url, "GET")
                resp = requests.get(
                    url,
                    headers=headers,
                    timeout=config.facilitator_timeout,
                    allow_redirects=False,
                )
                if resp.status_code == 200:
                    ok(
                        f"facilitator /supported answered 200 ({len(resp.content)} bytes)"
                    )
                else:
                    fail(f"facilitator /supported answered HTTP {resp.status_code}")
            except Exception as exc:
                fail(f"facilitator request failed: {type(exc).__name__}")

        if failures:
            raise CommandError(f"{len(failures)} check(s) failed")
        self.stdout.write(self.style.SUCCESS("all checks passed"))

    def _check_eviction(self, backend, ok, warn):
        """Best effort: the replay lock must not be evictable."""
        if not backend.endswith("RedisCache"):
            return
        try:
            client = cache._cache.get_client(write=True)
            policy = client.config_get("maxmemory-policy").get("maxmemory-policy")
        except Exception:
            warn("could not read Redis maxmemory-policy; confirm it is noeviction")
            return
        if policy == "noeviction":
            ok("redis maxmemory-policy=noeviction")
        else:
            warn(f"redis maxmemory-policy={policy}: replay locks could be evicted")
