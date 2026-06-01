#!/usr/bin/env python3
"""
Download Tree-Sitter parser bundles required by Nirjas.

SPDX-License-Identifier: LGPL-2.1

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Usage:
    python3 scripts/download_parsers.py
    python3 scripts/download_parsers.py --config language-pack.toml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tree_sitter_language_pack import download


_LANGUAGE_ALIASES = {
    "c#": "csharp",
    "c_sharp": "csharp",
    "shell": "bash",
    "shellscript": "bash",
}


class ParserDownloadError(Exception):
    """Raised when parser download config is invalid or download fails."""


def parse_language_config(config_path: Path) -> list[str]:
    """Parse `languages = [ ... ]` list from language-pack.toml."""

    if not config_path.exists():
        raise ParserDownloadError(f"Config file not found: {config_path}")

    config_text = config_path.read_text(encoding="utf-8")
    match = re.search(r"languages\s*=\s*\[(.*?)\]", config_text, flags=re.S)
    if match is None:
        raise ParserDownloadError(
            f"Could not find `languages = [ ... ]` in config: {config_path}"
        )

    languages_raw = match.group(1)
    languages = []
    for quoted_value in re.findall(r"['\"]([^'\"]+)['\"]", languages_raw):
        language_name = quoted_value.strip()
        if language_name:
            languages.append(language_name)

    if not languages:
        raise ParserDownloadError(f"No languages configured in: {config_path}")

    return languages


def normalize_language_names(language_names: list[str]) -> list[str]:
    """Normalize aliases and deduplicate while preserving order."""

    normalized_names: list[str] = []
    seen_languages: set[str] = set()

    for language_name in language_names:
        normalized_name = _LANGUAGE_ALIASES.get(language_name, language_name)
        if normalized_name in seen_languages:
            continue
        normalized_names.append(normalized_name)
        seen_languages.add(normalized_name)

    return normalized_names


def download_parsers(config_path: Path) -> int:
    """Download parser bundles from config file and return count."""

    configured_language_names = parse_language_config(config_path)
    language_names = normalize_language_names(configured_language_names)

    try:
        downloaded = download(language_names)
    except Exception as exc:  # pragma: no cover - depends on network/runtime
        raise ParserDownloadError(
            "Failed to download Tree-Sitter parsers. "
            f"Configured: {configured_language_names}. "
            f"Normalized: {language_names}. Error: {exc}"
        ) from exc

    return downloaded


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="Download Tree-Sitter language parsers required by Nirjas",
    )
    parser.add_argument(
        "--config",
        default="language-pack.toml",
        help="Path to parser configuration file (default: language-pack.toml)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)

    try:
        downloaded_count = download_parsers(config_path)
    except ParserDownloadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(
        "Tree-Sitter parser download complete. "
        f"Downloaded/verified parsers: {downloaded_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
