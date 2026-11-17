"""Exercise Release asset identity and real HTTP transfers without GitHub outages."""
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
import proxy_metadata
import proxy_sources

PAYLOAD = b"release asset bytes\n\x00\xff\r\n"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
TEST_TOKEN = "local-test-token-not-a-credential"
ASSET_ID = 123
WEB_URL = "https://github.com/kenzok8/openwrt-honk/releases/download/source-123/core.tar.gz"
API_URL = f"https://api.github.com/repos/kenzok8/openwrt-honk/releases/assets/{ASSET_ID}"


class AssetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get("Accept")))
        self.server.authorization.append(self.headers.get("Authorization"))
        if self.headers.get("Accept") != "application/octet-stream":
            self.send_error(400)
            return
        if self.path == "/unavailable":
            self.send_error(504)
            return
        if self.path == "/forbidden" or (
                self.path == "/authenticated" and
                self.headers.get("Authorization") != f"token {TEST_TOKEN}"):
            self.send_error(403)
            return
        if self.path == "/external-redirect":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_port}/asset")
            self.end_headers()
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/asset")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        pass


class ReleaseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.expected = {"name": "core.tar.gz", "url": WEB_URL, "sha256": DIGEST}
        self.remote = {"id": ASSET_ID, "name": "core.tar.gz", "url": API_URL,
                       "browser_download_url": WEB_URL, "digest": "sha256:" + DIGEST}

    def test_api_identity_preserves_original_url_and_digest(self):
        bound = proxy_metadata.honk_release_asset(self.expected, self.remote)
        self.assertEqual(bound, {**self.expected, "asset_id": ASSET_ID, "api_url": API_URL})
        self.assertNotIn("api_url", self.expected)

    def test_changed_identity_or_digest_is_rejected(self):
        changes = ({"id": "123"}, {"id": True}, {"id": 0}, {"name": "other.tar.gz"},
                   {"url": "https://example.invalid/asset"},
                   {"browser_download_url": WEB_URL.replace("source-123", "source-456")},
                   {"digest": "sha256:" + "0" * 64})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                proxy_metadata.honk_release_asset(self.expected, {**self.remote, **change})


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        # Isolate real gh requests from the developer's and CI runner's credentials.
        self.environment = patch.dict(os.environ, {
            "GH_CONFIG_DIR": str(self.root / "gh-config"), "GH_HOST": "github.com",
            "GH_TOKEN": TEST_TOKEN, "GITHUB_TOKEN": TEST_TOKEN,
            "GH_ENTERPRISE_TOKEN": TEST_TOKEN, "GITHUB_ENTERPRISE_TOKEN": TEST_TOKEN,
            "GH_DEBUG": "", "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AssetHandler)
        self.server.requests = []
        self.server.authorization = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def asset(self, name="core.tar.gz", route="/asset"):
        return {"name": name, "url": f"http://127.0.0.1:{self.server.server_port}/browser-download",
                "api_url": f"http://127.0.0.1:{self.server.server_port}{route}", "sha256": DIGEST}

    def test_download_follows_api_redirect_and_checks_payload(self):
        destination = self.root / "download"
        proxy_sources.download_verified(destination, self.asset(route="/redirect"))
        self.assertEqual(destination.read_bytes(), PAYLOAD)
        self.assertEqual(self.server.requests,
                         [("/redirect", "application/octet-stream"), ("/asset", "application/octet-stream")])

    def test_download_authenticates_with_existing_gh_credentials(self):
        destination = self.root / "download"
        proxy_sources.download_verified(destination, self.asset(route="/authenticated"))
        self.assertEqual(destination.read_bytes(), PAYLOAD)
        self.assertEqual(self.server.authorization, [f"token {TEST_TOKEN}"])

    def test_download_does_not_forward_token_to_redirected_host(self):
        destination = self.root / "download"
        proxy_sources.download_verified(destination, self.asset(route="/external-redirect"))
        self.assertEqual(destination.read_bytes(), PAYLOAD)
        self.assertEqual(self.server.authorization, [f"token {TEST_TOKEN}", None])

    def test_forbidden_request_fails_without_exposing_token_or_replacing_file(self):
        destination = self.root / "download"
        destination.write_bytes(b"existing")
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            proxy_sources.download_verified(destination, self.asset(route="/forbidden"))
        self.assertNotIn(TEST_TOKEN, str(raised.exception))
        self.assertEqual(destination.read_bytes(), b"existing")
        self.assertEqual(len(self.server.requests), 1)

    def test_http_error_fails_without_retry_or_browser_fallback(self):
        destination = self.root / "download"
        destination.write_bytes(b"existing")
        with self.assertRaises(subprocess.CalledProcessError):
            proxy_sources.download_verified(destination, self.asset(route="/unavailable"))
        self.assertEqual(destination.read_bytes(), b"existing")
        self.assertEqual(self.server.requests, [("/unavailable", "application/octet-stream")])

    def test_corrupt_payload_never_replaces_existing_destination(self):
        destination = self.root / "download"
        destination.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            proxy_sources.download_verified(destination, {**self.asset(), "sha256": "0" * 64})
        self.assertEqual(destination.read_bytes(), b"existing")

    def prepared_source(self):
        source = self.root / "source"
        source.mkdir()
        subprocess.run(["git", "init", "-q", str(source)], check=True, timeout=10)
        (source / "Makefile").write_text("verified package\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "Makefile"], check=True, timeout=10)
        (source / "ci").mkdir()
        (source / "honk").mkdir()
        (source / "honk/generated-provenance.json").write_bytes(PAYLOAD)
        receipt = {"assets": {"aarch64": self.asset(), "doona": self.asset("doona.tar.gz")},
                   "provenance": {"asset": self.asset()},
                   "files_sha256": proxy_sources.tracked_hashes(source)}
        (source / "ci/PROXY-SOURCE.json").write_text(json.dumps(receipt), encoding="utf-8")
        return source

    def test_stage_both_archives_then_reuse_only_verified_files(self):
        source = self.prepared_source()
        downloads = self.root / "dl"
        proxy_sources.fetch_honk_downloads(source, downloads)
        for name in ("core.tar.gz", "doona.tar.gz"):
            self.assertEqual((downloads / name).read_bytes(), PAYLOAD)
        proxy_sources.fetch_honk_downloads(source, downloads)
        self.assertEqual(len(self.server.requests), 2)
        (downloads / "core.tar.gz").write_bytes(b"corrupt cached file")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            proxy_sources.fetch_honk_downloads(source, downloads)
        self.assertEqual(len(self.server.requests), 2)

    def test_changed_prepared_package_is_rejected_before_download(self):
        source = self.prepared_source()
        (source / "Makefile").write_text("changed package\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Prepared package changed"):
            proxy_sources.fetch_honk_downloads(source, self.root / "dl")
        self.assertFalse(self.server.requests)


if __name__ == "__main__":
    unittest.main()
