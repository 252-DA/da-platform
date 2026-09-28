#!/usr/bin/env python3
"""Verify that every `materialize@<sha>` pin in a consumer's CI matches the
commit da-platform has actually committed for that dependency.

Consumer repos (worker, packages-ai, ...) run their own CI on their own
repo, so they cannot read da-platform's `.gitmodules`. Each one re-creates
the sibling layout by pinning a 40-char SHA directly in its workflow YAML:

    uses: 252-DA/core-chunking/.github/actions/materialize@<sha>

That is a second, independent pin sitting next to da-platform's submodule
gitlink (docs/embedding-service-migration.md §5.1). Bumping one does not
bump the other, so CI can silently build against different code than
Compose and local dev do. This script is the check that catches the drift.

Both sides are discovered rather than hardcoded: dependencies come from
`.gitmodules`, consumers are any top-level directory shipping its own
workflows. Adding a submodule or a service needs no edit here.

Only a consumer that is its own repo can actually drift, because GitHub
runs `.github/workflows/` from a repo root only. An in-tree service keeps
its workflows in a subdirectory of da-platform, where they never execute,
so a stale pin there is reported as a note rather than a failure.

Run from the da-platform repo root:
    python3 scripts/check_materialize_pins.py

A consumer intentionally lagging must be listed in
scripts/check_materialize_pins.exceptions.json with a reason, keyed
"<consumer>/<repo>". An exception waives the SHA match, not the check.

No third-party dependencies -- this runs in CI before any Python env is
set up for the consumers themselves.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCEPTIONS_FILE = Path(__file__).resolve().parent / "check_materialize_pins.exceptions.json"

# "252-DA/core-chunking/.github/actions/materialize@<40 hex>"
MATERIALIZE_RE = re.compile(
    r"[\w.-]+/([\w.-]+)/\.github/actions/materialize@([0-9a-f]{40})"
)


def submodule_repos() -> dict[str, str]:
    """Map GitHub repo name -> submodule path, read from .gitmodules.

    The repo name is what a consumer's `uses:` line refers to; the path is
    where da-platform checks it out. They differ (core-chunking lives at
    packages-ai/), which is exactly why this mapping has to be derived
    rather than assumed.
    """
    result = subprocess.run(
        ["git", "config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.(path|url)$"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}

    paths: dict[str, str] = {}
    urls: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        name = key.split(".", 2)[1] if key.count(".") >= 2 else None
        if name is None:
            continue
        if key.endswith(".path"):
            paths[name] = value
        elif key.endswith(".url"):
            urls[name] = value

    repos: dict[str, str] = {}
    for name, path in paths.items():
        url = urls.get(name, "")
        repo = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        if repo:
            repos[repo] = path
    return repos


def committed_gitlink(path: str) -> str | None:
    """Read the commit pinned in da-platform's own tree -- NOT the commit
    currently checked out in the submodule's working dir. `git submodule
    status` reports the latter, which can be ahead of what is committed if
    a dev bumped it locally and forgot to commit. We want to verify what
    has actually been chosen, so read the gitlink from the tree.
    """
    result = subprocess.run(
        ["git", "ls-tree", "HEAD", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    parts = result.stdout.strip().split()
    # "160000 commit <sha>\t<path>" -- mode 040000 means it is a plain
    # directory now (moved in-tree), not a submodule.
    if len(parts) < 3 or parts[1] != "commit":
        return None
    return parts[2]


def consumers() -> list[str]:
    """Every top-level directory that ships its own workflows. The root
    .github/ belongs to da-platform itself and is skipped."""
    found = []
    for entry in sorted(REPO_ROOT.iterdir()):
        if entry.is_dir() and (entry / ".github" / "workflows").is_dir():
            found.append(entry.name)
    return found


def materialize_pins(consumer: str) -> set[tuple[str, str]]:
    """(repo, sha) pairs pinned across a consumer's workflows. Commented
    lines are ignored -- a disabled step pins nothing."""
    pins: set[tuple[str, str]] = set()
    workflows_dir = REPO_ROOT / consumer / ".github" / "workflows"
    for wf in sorted(list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))):
        for line in wf.read_text().splitlines():
            if line.lstrip().startswith("#"):
                continue
            pins.update(MATERIALIZE_RE.findall(line))
    return pins


def load_exceptions() -> dict[str, str]:
    if not EXCEPTIONS_FILE.exists():
        return {}
    return json.loads(EXCEPTIONS_FILE.read_text())


def main() -> int:
    repos = submodule_repos()
    # A consumer only has live CI if it is its own repo. Workflows under an
    # in-tree directory are never executed by GitHub.
    own_repos = set(repos.values())
    exceptions = load_exceptions()
    problems: list[str] = []
    checked = 0

    for consumer in consumers():
        for repo, ci_sha in sorted(materialize_pins(consumer)):
            key = f"{consumer}/{repo}"

            path = repos.get(repo)
            if path is None:
                # The consumer materializes something da-platform does not
                # pin as a submodule -- it may have moved in-tree, or it may
                # never have been one. Either way there is nothing to
                # compare against, so warn instead of failing.
                print(
                    f"[check_materialize_pins] NOTE {key}: pins {repo}@{ci_sha[:12]}, "
                    f"but da-platform has no submodule for '{repo}' -- nothing to "
                    "compare. Moved in-tree?"
                )
                continue

            pinned = committed_gitlink(path)
            if pinned is None:
                print(
                    f"[check_materialize_pins] NOTE {key}: '{path}' is no longer a "
                    f"submodule in da-platform (now a plain directory), but {consumer} "
                    f"still materializes {repo}@{ci_sha[:12]} in CI."
                )
                continue

            if ci_sha == pinned:
                checked += 1
                continue

            if consumer not in own_repos:
                print(
                    f"[check_materialize_pins] NOTE {key}: CI pins {ci_sha[:12]}, "
                    f"gitlink is {pinned[:12]}. '{consumer}' lives in-tree, so this "
                    "workflow is inert -- GitHub runs .github/workflows/ from a repo "
                    "root only. Stale, but harmless until it is split out."
                )
                continue

            if key in exceptions:
                print(
                    f"[check_materialize_pins] ALLOWED {key}: CI pins {ci_sha[:12]}, "
                    f"gitlink is {pinned[:12]} -- reason: {exceptions[key]}"
                )
                continue

            problems.append(
                f"{key}: CI pins {repo}@{ci_sha} but da-platform's gitlink for "
                f"'{path}' is {pinned}. Bump the SHA in {consumer}'s workflow "
                f"(docs/embedding-service-migration.md §5.2), or declare an "
                f"exception in {EXCEPTIONS_FILE.name} keyed \"{key}\"."
            )

    if problems:
        print("\n[check_materialize_pins] FAILED:\n")
        for p in problems:
            print(f"  - {p}\n")
        return 1

    print(f"[check_materialize_pins] OK -- {checked} pin(s) match da-platform's gitlinks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
