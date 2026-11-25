"""Go-live prep for the paid API: Redis cache, Base mainnet, facilitator auth."""

import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from ..models import Episode, Podcast
from ..paid_api.adapters import X402FacilitatorAdapter
from ..paid_api.config import (
    BASE_MAINNET_NETWORK,
    BASE_MAINNET_USDC,
    PaidApiConfigError,
    get_config,
)
from .test_paid_api import ENABLED, PAYER, FakeAdapter, decode_header, payment_header

API_DIR = Path(__file__).resolve().parents[2]

MAINNET = {
    **ENABLED,
    "PAID_API_ALLOW_MAINNET": True,
    "PAID_API_NETWORK": BASE_MAINNET_NETWORK,
    "PAID_API_ASSET": BASE_MAINNET_USDC,
    "PAID_API_ASSET_NAME": "USD Coin",
    "PAID_API_ASSET_VERSION": "2",
}

REDIS_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}


def sample_hook(method, url, config):
    return {"Authorization": f"Bearer jwt-for-{method}-{url.rsplit('/', 1)[-1]}"}


def broken_hook(method, url, config):
    raise RuntimeError("no key")


NOT_CALLABLE = "not callable"


class SettingsCacheTest(SimpleTestCase):
    """settings/base.py picks the cache from REDIS_URL (fresh interpreter)."""

    def _cache_setting(self, redis_url):
        env = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}
        env.update(DJANGO_SECRET_KEY="x", PYTHONPATH=str(API_DIR))
        if redis_url:
            env["REDIS_URL"] = redis_url
        code = (
            "import json;from audio_processing.settings import base;"
            "print(json.dumps(getattr(base, 'CACHES', None)))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=API_DIR,
            env={**env, "PYTHONPATH": str(API_DIR)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        import json

        return json.loads(out.strip().splitlines()[-1])

    def test_redis_url_selects_redis_cache(self):
        caches = self._cache_setting("redis://redis:6379/1")
        default = caches["default"]
        self.assertEqual(
            default["BACKEND"], "django.core.cache.backends.redis.RedisCache"
        )
        self.assertEqual(default["LOCATION"], "redis://redis:6379/1")
        self.assertLessEqual(default["OPTIONS"]["socket_timeout"], 5)

    def test_no_redis_url_leaves_default_cache(self):
        self.assertIsNone(self._cache_setting(""))


class MainnetConfigTest(SimpleTestCase):
    def test_documented_values(self):
        self.assertEqual(BASE_MAINNET_NETWORK, "eip155:8453")
        self.assertEqual(
            BASE_MAINNET_USDC, "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        )

    def test_base_mainnet_usdc_accepted(self):
        with override_settings(**{**MAINNET, "DEBUG": False}, CACHES=REDIS_CACHES):
            config = get_config()
        self.assertEqual(config.network, "eip155:8453")
        self.assertEqual(config.asset, BASE_MAINNET_USDC)

    def test_asset_compared_case_insensitively(self):
        with override_settings(
            **{**MAINNET, "PAID_API_ASSET": BASE_MAINNET_USDC.lower()}
        ):
            self.assertEqual(get_config().network, "eip155:8453")

    def test_wrong_asset_on_base_mainnet_refused(self):
        for asset in ("0x" + "11" * 20, "0x036CbD53842c5426634e7929541eC2318f3dCF7e"):
            with self.subTest(asset=asset):
                with override_settings(**{**MAINNET, "PAID_API_ASSET": asset}):
                    with self.assertRaises(PaidApiConfigError):
                        get_config()

    def test_mainnet_still_needs_opt_in(self):
        with override_settings(**{**MAINNET, "PAID_API_ALLOW_MAINNET": False}):
            with self.assertRaises(PaidApiConfigError):
                get_config()

    def test_mainnet_needs_pay_to(self):
        with override_settings(**{**MAINNET, "PAID_API_PAY_TO": ""}):
            with self.assertRaises(PaidApiConfigError):
                get_config()


class FacilitatorAuthConfigTest(SimpleTestCase):
    def test_no_auth_by_default(self):
        with override_settings(**ENABLED):
            config = get_config()
        self.assertEqual(config.facilitator_headers, {})
        self.assertEqual(config.facilitator_auth_hook, "")

    def test_static_headers_and_bearer(self):
        with override_settings(
            **ENABLED,
            PAID_API_FACILITATOR_HEADERS='{"X-Api-Key": "k1"}',
            PAID_API_FACILITATOR_BEARER_TOKEN="tok",
        ):
            config = get_config()
        self.assertEqual(
            config.facilitator_headers,
            {"X-Api-Key": "k1", "Authorization": "Bearer tok"},
        )

    def test_bad_header_json_fails_closed(self):
        for raw in ("not json", "[1]", '{"a": 1}', '{"": "x"}'):
            with self.subTest(raw=raw):
                with override_settings(**ENABLED, PAID_API_FACILITATOR_HEADERS=raw):
                    with self.assertRaises(PaidApiConfigError):
                        get_config()

    def test_bad_hook_fails_closed(self):
        for path in ("no.such.module.fn", f"{__name__}.NOT_CALLABLE"):
            with self.subTest(path=path):
                with override_settings(**ENABLED, PAID_API_FACILITATOR_AUTH_HOOK=path):
                    with self.assertRaises(PaidApiConfigError):
                        get_config()

    def test_facilitator_url_with_credentials_or_query_refused(self):
        for url in (
            "https://user:pw@facilitator.test",
            "https://facilitator.test/x?key=secret",
        ):
            with self.subTest(url=url):
                with override_settings(**ENABLED, PAID_API_FACILITATOR_URL=url):
                    with self.assertRaises(PaidApiConfigError):
                        get_config()

    def test_secrets_not_in_repr(self):
        with override_settings(
            **ENABLED,
            PAID_API_FACILITATOR_BEARER_TOKEN="tok-secret",
            PAID_API_FACILITATOR_API_KEY_ID="id-secret",
            PAID_API_FACILITATOR_API_KEY_SECRET="key-secret",
        ):
            config = get_config()
        self.assertEqual(config.facilitator_key_id, "id-secret")
        self.assertEqual(config.facilitator_key_secret, "key-secret")
        text = repr(config)
        for secret in ("tok-secret", "id-secret", "key-secret"):
            self.assertNotIn(secret, text)


class FacilitatorAuthAdapterTest(SimpleTestCase):
    def _adapter(self, **extra):
        with override_settings(**ENABLED, **extra):
            config = get_config()
        session = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {
            "isValid": True,
            "success": True,
            "transaction": "0x1",
        }
        session.post.return_value = resp
        return X402FacilitatorAdapter(config, session=session), session

    def test_headers_sent_and_redirects_off(self):
        adapter, session = self._adapter(
            PAID_API_FACILITATOR_BEARER_TOKEN="tok",
            PAID_API_FACILITATOR_HEADERS='{"X-Api-Key": "k1"}',
        )
        adapter.verify({}, {})
        kwargs = session.post.call_args.kwargs
        self.assertEqual(
            kwargs["headers"], {"X-Api-Key": "k1", "Authorization": "Bearer tok"}
        )
        self.assertFalse(kwargs["allow_redirects"])

    def test_hook_called_per_request_and_wins(self):
        adapter, session = self._adapter(
            PAID_API_FACILITATOR_BEARER_TOKEN="static",
            PAID_API_FACILITATOR_AUTH_HOOK=f"{__name__}.sample_hook",
        )
        adapter.verify({}, {})
        self.assertEqual(
            session.post.call_args.kwargs["headers"]["Authorization"],
            "Bearer jwt-for-POST-verify",
        )
        adapter.settle({}, {})
        self.assertEqual(
            session.post.call_args.kwargs["headers"]["Authorization"],
            "Bearer jwt-for-POST-settle",
        )

    def test_hook_failure_on_settle_sends_nothing_and_is_definite(self):
        adapter, session = self._adapter(
            PAID_API_FACILITATOR_AUTH_HOOK=f"{__name__}.broken_hook"
        )
        with self.assertLogs("audio_processing.paid_api.adapters", "ERROR"):
            result = adapter.settle({}, {})
        self.assertFalse(result.success)
        self.assertTrue(result.definite)
        session.post.assert_not_called()

    def test_hook_failure_on_verify_raises(self):
        adapter, session = self._adapter(
            PAID_API_FACILITATOR_AUTH_HOOK=f"{__name__}.broken_hook"
        )
        with self.assertLogs("audio_processing.paid_api.adapters", "ERROR"):
            with self.assertRaises(Exception):
                adapter.verify({}, {})
        session.post.assert_not_called()


@override_settings(**ENABLED)
class CacheOutageTest(TestCase):
    """A broken cache must fail closed (503), never 500 or free content."""

    def setUp(self):
        cache.clear()
        podcast = Podcast.objects.create(name="Outage Show", url="https://e.com/o.xml")
        self.episode = Episode.objects.create(
            title="Outage episode",
            podcast=podcast,
            raw_audio_url="https://example.com/o.mp3",
            transcript="Some transcript text.",
            has_public_transcript=True,
        )
        self.url = reverse(
            "v1:api-v1-paid-transcript", kwargs={"slug": self.episode.slug}
        )
        self.adapter = FakeAdapter()
        patcher = patch(
            "audio_processing.paid_api.views.get_adapter", return_value=self.adapter
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _requirements(self):
        resp = self.client.get(self.url)
        return decode_header(resp["PAYMENT-REQUIRED"])["accepts"][0]

    def test_rate_limit_cache_down_returns_503(self):
        with patch(
            "audio_processing.paid_api.views.hit", side_effect=ConnectionError("down")
        ):
            with self.assertLogs("audio_processing.paid_api.views", "ERROR"):
                resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 503)

    def test_replay_lock_cache_down_returns_503_without_facilitator_call(self):
        req = self._requirements()
        with patch(
            "audio_processing.paid_api.views.cache.add",
            side_effect=ConnectionError("down"),
        ):
            with self.assertLogs("audio_processing.paid_api.views", "ERROR"):
                resp = self.client.get(
                    self.url, HTTP_PAYMENT_SIGNATURE=payment_header(req)
                )
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn("Some transcript", resp.content.decode())
        self.assertEqual(self.adapter.verify_calls, [])
        self.assertEqual(self.adapter.settle_calls, [])

    def test_cache_write_failure_after_settlement_still_serves(self):
        req = self._requirements()
        with patch(
            "audio_processing.paid_api.views.cache.set",
            side_effect=ConnectionError("down"),
        ):
            with self.assertLogs("audio_processing.paid_api.views", "ERROR"):
                resp = self.client.get(
                    self.url, HTTP_PAYMENT_SIGNATURE=payment_header(req)
                )
        self.assertEqual(resp.status_code, 200)
        # The lock key is still "pending", so the payment can't be replayed.
        again = self.client.get(self.url, HTTP_PAYMENT_SIGNATURE=payment_header(req))
        self.assertEqual(again.status_code, 402)


class PreflightCommandTest(SimpleTestCase):
    def _run(self, *args):
        out = StringIO()
        call_command("paid_api_check", *args, stdout=out)
        return out.getvalue()

    @override_settings(**{**ENABLED, "PAID_API_FACILITATOR_BEARER_TOKEN": "tok-secret"})
    def test_passes_and_hides_secrets(self):
        text = self._run()
        self.assertIn("config valid", text)
        self.assertIn("cache round-trip", text)
        self.assertIn("all checks passed", text)
        self.assertIn(ENABLED["PAID_API_PAY_TO"], text)
        self.assertNotIn("tok-secret", text)

    @override_settings(**{**ENABLED, "PAID_API_PAY_TO": ""})
    def test_bad_config_fails(self):
        with self.assertRaises(CommandError):
            self._run()

    @override_settings(**{**ENABLED, "DEBUG": False})
    def test_unshared_cache_fails(self):
        with self.assertRaises(CommandError):
            self._run()

    @override_settings(**{**MAINNET, "PAID_API_ALLOW_MAINNET": True})
    def test_mainnet_is_flagged(self):
        self.assertIn("MAINNET", self._run())

    @override_settings(
        **ENABLED, PAID_API_FACILITATOR_AUTH_HOOK=f"{__name__}.sample_hook"
    )
    def test_facilitator_probe_uses_auth_hook(self):
        resp = MagicMock(status_code=200, content=b"{}")
        with patch(
            "audio_processing.management.commands.paid_api_check.requests.get",
            return_value=resp,
        ) as get:
            text = self._run("--facilitator")
        self.assertEqual(get.call_args.args[0], "https://facilitator.test/supported")
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"],
            "Bearer jwt-for-GET-supported",
        )
        self.assertIn("/supported answered 200", text)

    @override_settings(**ENABLED)
    def test_facilitator_probe_failure_fails(self):
        resp = MagicMock(status_code=401, content=b"")
        with patch(
            "audio_processing.management.commands.paid_api_check.requests.get",
            return_value=resp,
        ):
            with self.assertRaises(CommandError):
                self._run("--facilitator")
