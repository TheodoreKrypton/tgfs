"""Persistent GitHub metadata cache helpers.

A SHA-pinned configured ref is immutable, so a matching cache can be used without
network access. Mutable refs are checked with one branch request for their root
tree SHA before the cached tree is trusted. Bad cache files are cache misses.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .gh_directory import GithubConfig

CACHE_VERSION = 1
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass
class CachedMetadata:
    metadata: dict[str, Any]
    resolved_tree_sha: str
    current_tree_sha: Optional[str] = None


def is_sha_pinned(ref: str) -> bool:
    return bool(_SHA_RE.fullmatch(ref))


def load_cache(path: Path, repo: str, configured_ref: str) -> Optional[CachedMetadata]:
    """Load a cache envelope, treating every malformed input as a cache miss."""
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(envelope, dict):
            return None
        if envelope.get("cache_version") != CACHE_VERSION:
            return None
        if envelope.get("repo") != repo or envelope.get("configured_ref") != configured_ref:
            return None
        metadata = envelope.get("metadata")
        resolved_tree_sha = envelope.get("resolved_tree_sha")
        if not isinstance(metadata, dict) or not isinstance(resolved_tree_sha, str):
            return None
        return CachedMetadata(metadata=metadata, resolved_tree_sha=resolved_tree_sha)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def resolve_and_check_freshness(ghc: GithubConfig, cached: CachedMetadata) -> bool:
    """Check a mutable ref with one API call; SHA-pinned refs need none."""
    if is_sha_pinned(ghc.commit):
        return True
    try:
        cached.current_tree_sha = ghc.repo.get_branch(ghc.commit).commit.commit.tree.sha
    except Exception:
        return False
    return cached.current_tree_sha == cached.resolved_tree_sha
