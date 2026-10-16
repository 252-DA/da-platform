#!/usr/bin/env python3
"""Keep contracts/proto/llm_model_catalog.json in step with the ai-sdk catalog.

The page where an admin picks a model per task (web /manage/models) writes
through core-api, and core-api must refuse any profile the workers cannot
resolve. The authority for "which profiles exist" is PROFILES in
ai-sdk/src/ai_runtime/catalog.py, but core-api is TypeScript in another repo,
so it reads this JSON copy instead. contracts/proto/ is the directory both
core-api and web already mount at /app/proto.

The tasks listed are the ones a worker resolves per job through
``TaskRoles.role(...)`` in worker/worker/container.py -- the only tasks a
binding in llm_model_bindings actually changes. ``use_cases`` are the
llm_usage_logs.use_case values each task's calls are logged under, so the
page can show what a task last ran on.

Run from the da-platform repo root:
    python3 scripts/check_model_catalog.py          # fail if the JSON is stale
    python3 scripts/check_model_catalog.py --write  # regenerate it

Stdlib only: catalog.py is loaded on its own, without the ai_runtime package
(whose __init__ pulls in pydantic).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PY = ROOT / "ai-sdk/src/ai_runtime/catalog.py"
CONTAINER_PY = ROOT / "worker/worker/container.py"
OUTPUT = ROOT / "contracts/proto/llm_model_catalog.json"

# Task -> the llm_usage_logs.use_case values its calls are logged under.
# Writer and judge are shared by quiz and lesson cards (worker/container.py).
TASK_USE_CASES: dict[str, list[str]] = {
    "quiz_generation": [
        "quiz_generation",
        "quiz_regeneration",
        "card_generation",
        "card_regeneration",
    ],
    "quiz_verification": [
        "quiz_verification",
        "card_verification",
        "answer_grading",
        "essay_grading",
    ],
    "enrichment": ["enrichment_cards", "enrichment_quiz"],
}


def _load_catalog():
    spec = importlib.util.spec_from_file_location("_ai_runtime_catalog", CATALOG_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolves annotations through it
    spec.loader.exec_module(module)
    return module


def _routed_tasks(catalog) -> set[str]:
    """Task constants the worker passes to ``.role(...)``, as task strings."""
    names = set(re.findall(r"\.role\(([A-Z_]+)\)", CONTAINER_PY.read_text(encoding="utf-8")))
    return {getattr(catalog, name) for name in names}


def build() -> dict:
    catalog = _load_catalog()
    profiles = [
        {"name": p.name, "provider": p.provider, "model": p.model}
        for p in sorted(catalog.PROFILES.values(), key=lambda p: p.name)
        if not p.internal
    ]
    tasks = [
        {
            "task": task,
            "default_profile": catalog.TASK_DEFAULTS.get(task, catalog.DEFAULT_PROFILE),
            "use_cases": use_cases,
        }
        for task, use_cases in TASK_USE_CASES.items()
    ]
    return {
        "$comment": (
            "Generated from ai-sdk/src/ai_runtime/catalog.py by "
            "scripts/check_model_catalog.py --write. Do not edit by hand."
        ),
        "profiles": profiles,
        "tasks": tasks,
    }


def problems(catalog_json: dict) -> list[str]:
    catalog = _load_catalog()
    out: list[str] = []
    routed = _routed_tasks(catalog)
    listed = set(TASK_USE_CASES)
    if routed != listed:
        out.append(
            "tasks resolved per job in worker/container.py "
            f"{sorted(routed)} != TASK_USE_CASES {sorted(listed)}"
        )
    names = {p["name"] for p in catalog_json["profiles"]}
    for task in catalog_json["tasks"]:
        if task["default_profile"] not in names:
            out.append(f"default profile of {task['task']} is not selectable: {task['default_profile']}")
    return out


def main(argv: list[str]) -> int:
    expected = build()
    issues = problems(expected)
    if issues:
        for issue in issues:
            print(f"model catalog: {issue}", file=sys.stderr)
        return 1

    text = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    if "--write" in argv:
        OUTPUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
        print(
            f"{OUTPUT.relative_to(ROOT)} is stale: run "
            "python3 scripts/check_model_catalog.py --write",
            file=sys.stderr,
        )
        return 1
    print("model catalog: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
