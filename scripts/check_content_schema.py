#!/usr/bin/env python3
"""Keep the generated-content JSON contract, the prompt that asks an LLM for
it, and the model that parses the reply from drifting apart.

The quiz item shape is written down four times across three repos: as JSON
Schema in contracts/artifacts/v1/content-generation.json (the authority), as
a literal JSON example inside the prompt in worker, as a Pydantic model in
the same worker file, and again in chunking.proto and web's review route.
Nothing tied the first three together, so a field added to the contract
would simply never be asked for, and a field renamed in the prompt would
parse into nothing.

The split between LLM-provided and code-filled fields is real and
intentional: the model must not invent `model_id` (the runtime knows it) or
`position` (balanced_positions computes it). That split was implicit; this
check makes it explicit and enforced.

Invariant:
    prompt fields == pydantic fields == contract fields - CODE_FILLED

Run from the da-platform repo root:
    python3 scripts/check_content_schema.py

No third-party dependencies -- this runs in CI before any Python env is set
up for the consumers.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "contracts" / "artifacts" / "v1" / "content-generation.json"
QUIZ_USE_CASE = REPO_ROOT / "worker" / "worker" / "use_cases" / "generate_curriculum_quiz.py"

PYDANTIC_MODEL = "_CurriculumQuestion"

# Fields the contract requires but the LLM must NOT supply, with the reason.
# Anything added here is a deliberate exclusion, not a gap to paper over.
CODE_FILLED = {
    "model_id": "set from self._llm_client.model_id -- the runtime knows it, the model would guess",
    "position": "computed by balanced_positions() so correct answers spread evenly",
}


def contract_fields() -> set[str]:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return set(schema["definitions"]["quizItem"]["properties"])


def prompt_fields(source: str) -> set[str]:
    """Field names in the literal JSON example the prompt shows the model.

    The example is spliced across adjacent string literals, so read it from
    the source text rather than trying to evaluate the f-string.
    """
    match = re.search(r'\{"questions":\s*\[\s*\{(.*?)\]\}', source, re.S)
    if match is None:
        return set()
    return set(re.findall(r'"(\w+)"\s*:', match.group(1)))


def pydantic_fields(source: str) -> set[str]:
    """Annotated attributes of the model that parses the reply, via AST so a
    reformat or an added validator cannot fool it."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == PYDANTIC_MODEL:
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    return set()


def main() -> int:
    if not QUIZ_USE_CASE.exists():
        print(
            f"[check_content_schema] {QUIZ_USE_CASE.relative_to(REPO_ROOT)} not found -- "
            "the worker submodule is probably not checked out. Nothing to check."
        )
        return 0

    source = QUIZ_USE_CASE.read_text(encoding="utf-8")
    contract = contract_fields()
    prompt = prompt_fields(source)
    pydantic = pydantic_fields(source)
    expected = contract - set(CODE_FILLED)

    problems: list[str] = []

    unknown = set(CODE_FILLED) - contract
    if unknown:
        problems.append(
            f"CODE_FILLED names {sorted(unknown)}, which the contract does not define. "
            "Either the field was renamed in the contract or the exclusion is stale."
        )

    if not prompt:
        problems.append("could not find the JSON example in the prompt -- has its shape changed?")
    elif prompt != expected:
        missing, extra = sorted(expected - prompt), sorted(prompt - expected)
        problems.append(
            f"the prompt asks for {sorted(prompt)}, but the contract expects the model to "
            f"supply {sorted(expected)}."
            + (f" Never asked for: {missing}." if missing else "")
            + (f" Asked for but not in the contract: {extra}." if extra else "")
        )

    if not pydantic:
        problems.append(f"could not find class {PYDANTIC_MODEL} -- was it renamed?")
    elif pydantic != expected:
        missing, extra = sorted(expected - pydantic), sorted(pydantic - expected)
        problems.append(
            f"{PYDANTIC_MODEL} parses {sorted(pydantic)}, but the contract expects "
            f"{sorted(expected)}."
            + (f" Silently dropped: {missing}." if missing else "")
            + (f" Parsed but not in the contract: {extra}." if extra else "")
        )

    if problems:
        print("[check_content_schema] FAILED:\n")
        for p in problems:
            print(f"  - {p}\n")
        print(f"  Contract: {CONTRACT.relative_to(REPO_ROOT)}")
        print(f"  Prompt + model: {QUIZ_USE_CASE.relative_to(REPO_ROOT)}\n")
        return 1

    print(
        f"[check_content_schema] OK -- contract, prompt and {PYDANTIC_MODEL} agree on "
        f"{len(expected)} LLM-supplied field(s); {len(CODE_FILLED)} filled by code:"
    )
    for name, why in sorted(CODE_FILLED.items()):
        print(f"    {name}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
