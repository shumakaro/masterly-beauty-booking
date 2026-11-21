"""Первый локальный запуск создает только отсутствующий ключ и сохраняет настройки."""

import re
import subprocess
import sys
from pathlib import Path

import pytest


def initializer(tmp_path):
    script = tmp_path / "backend/scripts/configure_local.py"
    script.parent.mkdir(parents=True)
    script.write_bytes((Path(__file__).parents[1] / "scripts/configure_local.py").read_bytes())
    return script


@pytest.mark.parametrize(
    "key_line", ["JWT_SECRET=", "JWT_SECRET=   ", "   JWT_SECRET =   ", "# JWT_SECRET=example"]
)
def test_empty_key_does_not_consume_following_settings_and_is_initialized_once(tmp_path, key_line):
    script = initializer(tmp_path)
    (tmp_path / ".env.example").write_text(
        key_line + "\n# Keep this comment\nCOOKIE_SECURE=false\n", encoding="utf-8"
    )
    first = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True
    )
    target = tmp_path / ".env"
    content = target.read_text(encoding="utf-8")
    key = re.search(r"^JWT_SECRET=([^\n]+)$", content, flags=re.MULTILINE).group(1)
    assert len(key) >= 32
    assert "# Keep this comment\nCOOKIE_SECURE=false" in content
    assert key not in first.stdout + first.stderr
    second = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True
    )
    assert target.read_text(encoding="utf-8") == content
    assert key not in second.stdout + second.stderr


def test_existing_private_key_is_preserved_without_echo(tmp_path):
    script = initializer(tmp_path)
    private = "private-test-sentinel-do-not-echo-123456789"
    content = f"JWT_SECRET={private}\nCOOKIE_SECURE=false\n"
    (tmp_path / ".env").write_text(content, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True
    )
    assert (tmp_path / ".env").read_text(encoding="utf-8") == content
    assert private not in result.stdout + result.stderr
