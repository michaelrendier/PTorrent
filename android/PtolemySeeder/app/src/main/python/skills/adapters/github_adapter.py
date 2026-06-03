"""
skills/adapters/github_adapter.py — GitHub repository adapter.
Pure Python. urllib only. No requests library.

Handles:
  mode: github_repo      stream code files from a repository
  mode: github_dataset   discover and stream dataset files from a repo

source fields:
  repo          str         "owner/repo"
  branch        str         branch name (default "main")
  paths         list[str]   directory paths to search (default [""])
  extensions    list[str]   file extensions to include (default [".py"])
  value_col     str         ignored for corpus mode
  pat           str         GitHub PAT for higher rate limits (optional)
                            set via env var PTOL_GITHUB_PAT
  max_files     int         maximum files to stream (default 500)

GitHub API v3 (REST). Zero-scope PAT = rate limit 5000/hr vs 60/hr.
"""

from __future__ import annotations
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
import time
from typing import Iterator, Optional, List

from skills.adapters import DataAdapter, Row

_API = "https://api.github.com"
_RATE_SLEEP = 0.1   # seconds between requests (polite crawl)


def _get(url: str, pat: Optional[str] = None,
         accept: str = "application/vnd.github+json") -> dict | list | None:
    headers = {
        "Accept":               accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":           "PTorrent/2.0 (research corpus seeder)",
    }
    if pat:
        headers["Authorization"] = f"Bearer {pat}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            time.sleep(60)  # rate limited — wait
        return None
    except Exception:
        return None


def _get_pat(source: dict) -> Optional[str]:
    return (source.get("pat")
            or os.environ.get("PTOL_GITHUB_PAT")
            or os.environ.get("PTOL_SEED_TOKEN"))


def _list_tree(repo: str, branch: str, pat: Optional[str]) -> List[dict]:
    """Return flat list of all files in the repo tree."""
    url = f"{_API}/repos/{repo}/git/trees/{branch}?recursive=1"
    tree = _get(url, pat)
    if not tree or "tree" not in tree:
        return []
    return [item for item in tree["tree"] if item.get("type") == "blob"]


def _get_file_content(repo: str, path: str, pat: Optional[str]) -> str:
    """Fetch file content via GitHub Contents API. Returns UTF-8 text."""
    url = f"{_API}/repos/{repo}/contents/{urllib.parse.quote(path)}"
    data = _get(url, pat)
    if not data or "content" not in data:
        return ""
    try:
        content_b64 = data["content"].replace("\n", "")
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _phonebook_entry(repo: str, release: dict, pat: Optional[str]) -> dict:
    """Generate a phonebook .ptorrent dict from a GitHub release asset."""
    return {
        "ptorrent_version": "1.0",
        "type": "phonebook",
        "name": f"{repo} — {release.get('name', 'release')}",
        "primary_tags": ["DATASET", "GITHUB"],
        "color": "silver",
        "description": release.get("body", "")[:200],
        "phonebook": {
            "dataset_url": f"https://github.com/{repo}",
            "license": "see repository",
            "last_verified": time.strftime("%Y-%m-%d"),
            "dumps": [
                {
                    "url": asset["browser_download_url"],
                    "format": asset["name"].split(".")[-1].upper(),
                    "size_gb": round(asset["size"] / 1e9, 3),
                    "update_freq": "per-release",
                    "last_verified": time.strftime("%Y-%m-%d"),
                }
                for asset in release.get("assets", [])
                if asset.get("browser_download_url")
            ],
        },
    }


class GitHubAdapter(DataAdapter):
    NAME = "github_repo"

    def probe(self, source: dict) -> dict:
        repo   = source.get("repo", "")
        branch = source.get("branch", "main")
        pat    = _get_pat(source)
        dm: dict = {
            "native_format": "GitHub repository",
            "access": {"mode": "github_repo"},
            "repo": repo,
        }

        info = _get(f"{_API}/repos/{repo}", pat)
        if not info:
            dm["error"] = f"Cannot access repo: {repo}"
            dm["confidence"] = 0.0
            return dm

        dm["description"]  = info.get("description", "")
        dm["default_branch"] = info.get("default_branch", branch)
        dm["topics"]       = info.get("topics", [])
        dm["license"]      = (info.get("license") or {}).get("spdx_id", "")
        dm["stars"]        = info.get("stargazers_count", 0)
        dm["language"]     = info.get("language", "")
        dm["confidence"]   = 0.90
        dm["type"]         = "code_corpus"

        # Check for dataset markers
        if any(t in dm["topics"] for t in ["dataset", "open-data", "data"]):
            dm["type"] = "dataset_repo"

        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        repo       = source.get("repo", "")
        branch     = source.get("branch", "main")
        paths      = source.get("paths", [""])
        extensions = source.get("extensions", [".py"])
        max_files  = int(source.get("max_files", 500))
        pat        = _get_pat(source)

        ext_set = {e.lower() for e in extensions}

        tree = _list_tree(repo, branch, pat)
        if not tree:
            return

        count = 0
        for item in tree:
            if count >= max_files:
                break

            file_path = item.get("path", "")
            # Filter by paths
            if paths and paths != [""]:
                if not any(file_path.startswith(p.rstrip("/") + "/")
                           or file_path.startswith(p)
                           for p in paths):
                    continue

            # Filter by extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext_set and ext not in ext_set:
                continue

            content = _get_file_content(repo, file_path, pat)
            if not content.strip():
                continue

            time.sleep(_RATE_SLEEP)

            yield {
                "_adapter": "github",
                "_source":   f"github:{repo}/{file_path}",
                "_row_idx":  count,
                "value":     float(len(content)),  # proxy: file size
                "file_path": file_path,
                "extension": ext,
                "content":   content,    # full text for corpus training
                "raw": {
                    "repo":   repo,
                    "path":   file_path,
                    "size":   item.get("size", 0),
                },
            }
            count += 1


ADAPTER_CLASS = GitHubAdapter
