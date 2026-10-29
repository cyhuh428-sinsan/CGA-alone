"""CGA Studio 웹 의존성의 보안 버전 회귀를 방지한다."""

from __future__ import annotations

import json
from pathlib import Path


WEB_DIR = Path(__file__).resolve().parents[2] / "web"
PACKAGE_JSON = WEB_DIR / "package.json"
PACKAGE_LOCK = WEB_DIR / "package-lock.json"


def _version_tuple(value: str) -> tuple[int, ...]:
    core = value.split("-", 1)[0]
    return tuple(int(part) for part in core.split("."))


def test_security_sensitive_web_dependencies_are_pinned() -> None:
    manifest = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    assert manifest["dependencies"]["next"] == "16.4.3"
    assert manifest["overrides"]["postcss"] == "8.5.29"
    assert manifest["overrides"]["sharp"] == "0.35.5"


def test_locked_web_dependencies_meet_security_minimums() -> None:
    lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
    packages = lock["packages"]

    assert _version_tuple(packages["node_modules/next"]["version"]) >= (16, 4, 3)
    assert _version_tuple(packages["node_modules/baseline-browser-mapping"]["version"]) >= (2, 11, 0)
    assert _version_tuple(packages["node_modules/postcss"]["version"]) >= (8, 5, 29)
    assert _version_tuple(packages["node_modules/nanoid"]["version"]) >= (3, 3, 20)
    assert _version_tuple(packages["node_modules/sharp"]["version"]) >= (0, 35, 5)
    assert _version_tuple(packages["node_modules/source-map-js"]["version"]) >= (1, 2, 2)
