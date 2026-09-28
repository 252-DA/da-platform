#!/usr/bin/env python3
"""Verify that the `service-sdk` commit pinned for local dev/Compose (the
git submodule gitlink committed in da-platform) matches the commit each
consumer's own CI pins via its `.github/actions/materialize` step.

These are two independent pins (docs/embedding-service-migration.md §5.1)
that do not sync automatically:
  - Dev/Compose pin: the gitlink for `service-sdk` committed in da-platform.
  - Consumer CI pin: the SHA in `uses: 252-DA/service-sdk/.github/actions/
    materialize@<sha>` inside each consumer repo's own workflow YAML.

Run from the da-platform repo root:
    python3 scripts/check_service_sdk_pins.py

A consumer intentionally lagging behind must be listed in
scripts/check_service_sdk_pins.exceptions.json with a reason — an exception
still requires a materialize step to exist, it only waives the SHA match.
Format: {"<consumer>": "<reason>"}.

No third-party dependencies — this runs in CI before any Python env is set
up for the consumers themselves.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SDK_PATH = "service-sdk"
CONSUMERS = ["packages-ai", "worker", "embedding-service", "mcp-service"]
MATERIALIZE_RE = re.compile(
    r"252-DA/service-sdk/\.github/actions/materialize@([0-9a-f]{40})"
)
EXCEPTIONS_FILE = Path(__file__).resolve().parent / "check_service_sdk_pins.exceptions.json"


def committed_submodule_sha(path: str) -> str | None:
    """Read the commit pinned in da-platform's own tree — NOT the commit
    currently checked out in the submodule's working dir (`git submodule
    status` would report that, and it can be ahead of what's committed if a
    dev bumped it locally and forgot to commit). We want to check what's
    actually been committed, so read the gitlink from the tree instead."""
    result = subprocess.run(
        ["git", "ls-tree", "HEAD", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    line = result.stdout.strip()
    if not line:
        return None
    # format: "160000 commit <sha>\t<path>"
    parts = line.split()
    if len(parts) < 3 or parts[1] != "commit":
        return None
    return parts[2]


def workflow_files(consumer: str) -> list[Path]:
    workflows_dir = REPO_ROOT / consumer / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    return sorted(list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml")))


def materialize_shas(consumer: str) -> set[str]:
    shas: set[str] = set()
    for wf in workflow_files(consumer):
        shas.update(MATERIALIZE_RE.findall(wf.read_text()))
    return shas


def load_exceptions() -> dict[str, str]:
    if not EXCEPTIONS_FILE.exists():
        return {}
    return json.loads(EXCEPTIONS_FILE.read_text())


def main() -> int:
    pinned_sha = committed_submodule_sha(SDK_PATH)
    if pinned_sha is None:
        print(
            f"[check_service_sdk_pins] '{SDK_PATH}' is not yet a registered "
            "submodule in da-platform — nothing to check. This is expected "
            "before service-sdk has been split into its own repo."
        )
        return 0

    exceptions = load_exceptions()
    problems: list[str] = []

    for consumer in CONSUMERS:
        consumer_dir = REPO_ROOT / consumer
        if not consumer_dir.is_dir():
            continue  # not scaffolded as its own repo yet — nothing to check

        shas = materialize_shas(consumer)

        if not shas:
            if consumer in exceptions:
                continue
            problems.append(
                f"{consumer}: no 'service-sdk/.github/actions/materialize@<sha>' "
                "step found in any workflow, and no exception declared in "
                f"{EXCEPTIONS_FILE.name}."
            )
            continue

        if pinned_sha in shas:
            continue

        if consumer in exceptions:
            print(
                f"[check_service_sdk_pins] {consumer} pins service-sdk@{sorted(shas)}, "
                f"da-platform's submodule is at {pinned_sha} — allowed, reason: "
                f"{exceptions[consumer]}"
            )
            continue

        problems.append(
            f"{consumer}: CI pins service-sdk@{sorted(shas)}, but da-platform's "
            f"submodule gitlink is {pinned_sha}. Update the workflow SHA "
            f"(docs/embedding-service-migration.md §5.2 step 4), or add an "
            f"exception to {EXCEPTIONS_FILE.name} with a reason."
        )

    if problems:
        print("[check_service_sdk_pins] FAILED:\n")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(
        "[check_service_sdk_pins] OK — all consumer CI pins match "
        "da-platform's service-sdk commit."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
