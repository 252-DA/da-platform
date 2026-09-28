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

STORED_MODEL_FILE = (
    REPO_ROOT / "packages-ai" / "src" / "document_chunk" / "domain" / "ports" / "metadata_store.py"
)
STORED_MODEL = "StoredQuizItem"

# Contract fields the LLM must not supply, each naming the attribute on
# StoredQuizItem that actually carries it. The attribute is verified to
# exist -- an entry here is a claim about code, not a note. If a contract
# field is neither asked of the model nor listed here, no code produces it
# and the check says so rather than quietly subtracting it.
CODE_FILLED = {
    "model_id": "model_id",
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


def stored_model_fields() -> set[str]:
    """Annotated attributes of the model that is actually persisted."""
    if not STORED_MODEL_FILE.exists():
        return set()
    tree = ast.parse(STORED_MODEL_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == STORED_MODEL:
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    return set()


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


def main(argv: list[str]) -> int:
    # A required CI check must fail when its input is gone, otherwise losing
    # the submodule silently turns the check into a no-op -- the failure mode
    # check_service_sdk_pins.py spent weeks in. Skipping is opt-in and loud.
    allow_missing = "--allow-missing" in argv
    for path in (QUIZ_USE_CASE, STORED_MODEL_FILE):
        if path.exists():
            continue
        rel = path.relative_to(REPO_ROOT)
        if allow_missing:
            print(f"[check_content_schema] SKIPPED -- {rel} not found (--allow-missing).")
            return 0
        print(
            f"[check_content_schema] FAILED: {rel} not found. Check out the submodules "
            "(git submodule update --init), or pass --allow-missing to skip deliberately."
        )
        return 1

    source = QUIZ_USE_CASE.read_text(encoding="utf-8")
    contract = contract_fields()
    prompt = prompt_fields(source)
    pydantic = pydantic_fields(source)
    stored = stored_model_fields()
    expected = contract - set(CODE_FILLED)

    problems: list[str] = []

    unknown = set(CODE_FILLED) - contract
    if unknown:
        problems.append(
            f"CODE_FILLED names {sorted(unknown)}, which the contract does not define. "
            "Either the field was renamed in the contract or the exclusion is stale."
        )

    # An exclusion has to point at an attribute that exists. Otherwise the
    # check just subtracts a field nobody produces and calls it agreement.
    for field, attr in sorted(CODE_FILLED.items()):
        if attr not in stored:
            problems.append(
                f"CODE_FILLED maps contract field {field!r} to {STORED_MODEL}.{attr}, "
                f"which does not exist. {STORED_MODEL} has {sorted(stored)}."
            )

    if not prompt:
        problems.append("could not find the JSON example in the prompt -- has its shape changed?")
    elif prompt != expected:
        missing, extra = sorted(expected - prompt), sorted(prompt - expected)
        for field in list(missing):
            # Distinguish "the prompt forgot to ask" from "nothing anywhere
            # produces this" -- they need different fixes.
            if field not in stored:
                missing.remove(field)
                problems.append(
                    f"contract requires {field!r}, but the prompt does not ask the model for it "
                    f"and no {STORED_MODEL} attribute carries it. No code produces this field; "
                    "either implement it or drop it from the contract."
                )
        if missing or extra:
            problems.append(
                f"the prompt asks for {sorted(prompt)}, but the contract expects the model to "
                f"supply {sorted(expected)}."
                + (f" Never asked for: {missing}." if missing else "")
                + (f" Asked for but not in the contract: {extra}." if extra else "")
            )

    if not pydantic:
        problems.append(f"could not find class {PYDANTIC_MODEL} -- was it renamed?")
    elif pydantic != prompt and prompt:
        missing, extra = sorted(prompt - pydantic), sorted(pydantic - prompt)
        problems.append(
            f"{PYDANTIC_MODEL} parses {sorted(pydantic)}, but the prompt asks for "
            f"{sorted(prompt)}."
            + (f" Silently dropped: {missing}." if missing else "")
            + (f" Parsed but never asked for: {extra}." if extra else "")
        )

    if problems:
        print("[check_content_schema] FAILED:\n")
        for problem in problems:
            print(f"  - {problem}\n")
        print(f"  Contract: {CONTRACT.relative_to(REPO_ROOT)}")
        print(f"  Prompt + parser: {QUIZ_USE_CASE.relative_to(REPO_ROOT)}")
        print(f"  Persisted model: {STORED_MODEL_FILE.relative_to(REPO_ROOT)}\n")
        return 1

    print(
        f"[check_content_schema] OK -- contract, prompt and {PYDANTIC_MODEL} agree on "
        f"{len(prompt)} LLM-supplied field(s); {len(CODE_FILLED)} filled by code:"
    )
    for field, attr in sorted(CODE_FILLED.items()):
        print(f"    {field} <- {STORED_MODEL}.{attr}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
