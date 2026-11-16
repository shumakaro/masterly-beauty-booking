import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from configure_compose import settings


class ConfigurationTests(unittest.TestCase):
    def test_local_http_is_loopback_only_and_secrets_are_independent(self):
        value = settings("http://127.0.0.1:8080")
        self.assertEqual(value["COOKIE_SECURE"], "false")
        self.assertEqual(value["WEB_BIND"], "127.0.0.1")
        self.assertNotEqual(
            value["POSTGRES_PASSWORD"], value["POSTGRES_ADMIN_PASSWORD"]
        )
        self.assertGreaterEqual(len(value["JWT_SECRET"]), 64)

    def test_public_origin_requires_https(self):
        with self.assertRaises(ValueError):
            settings("http://masterly.example")
        self.assertEqual(settings("https://masterly.example")["COOKIE_SECURE"], "true")

    def test_rejects_credentials_paths_and_config_injection(self):
        for origin in [
            "https://user:pass@example.com",
            "https://example.com/path",
            "https://*.example.com",
            "https://example.com;",
            "https://example.com\nx",
        ]:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                settings(origin)

    def test_refuses_to_overwrite_private_settings(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            destination = Path(folder) / ".env.compose"
            destination.write_text("private-sentinel", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("configure_compose.py")),
                    "--output",
                    str(destination),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                destination.read_text(encoding="utf-8"), "private-sentinel"
            )
            self.assertNotIn("private-sentinel", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
