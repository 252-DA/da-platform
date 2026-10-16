#!/usr/bin/env python3
"""Keep the generated-content JSON contract, the prompt that asks an LLM for
it, and the model that parses the reply from drifting apart.

Checked for every generated shape in SPECS: quiz items and lesson cards.

The quiz item shape is written down four times across three repos: as JSON
Schema in contracts/artifacts/v1/content-generation.json (the authority), as
a literal JSON example inside the prompt in worker/worker/prompts/, as a
Pydantic model in the worker use case, and again in chunking.proto and web's
review route. Each question type (MCQ_SINGLE, MCQ_MULTI, ...) has its own
shape, so each is checked against its own contract definition, and a type
added to the prompt without a contract definition fails the check.
Nothing tied the first three together, so a field added to the contract
would simply never be asked for, and a field renamed in the prompt would
parse into nothing.

The split between LLM-provided and code-filled fields is real and
intentional: the model must not invent `model_id` (the runtime knows it) or
`position` (balanced_positions computes it). That split was implicit; this
check makes it explicit and enforced.

Invariant, per shape:
    prompt fields == pydantic fields == contract fields - code_filled

Run from the da-platform repo root:
    python3 scripts/check_content_schema.py

No third-party dependencies -- this runs in CI before any Python env is set
up for the consumers. The prompt modules are imported (they are stdlib-only)
rather than scraped, because the JSON example is now assembled from constants:
reading the source text would only see the pieces.
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "contracts" / "artifacts" / "v1" / "content-generation.json"
WORKER_ROOT = REPO_ROOT / "worker"
USE_CASES = WORKER_ROOT / "worker" / "use_cases"
PROMPTS = WORKER_ROOT / "worker" / "prompts"
STORED_MODEL_FILE = (
    REPO_ROOT / "packages-ai" / "src" / "document_chunk" / "domain" / "ports" / "metadata_store.py"
)


@dataclass(frozen=True)
class Spec:
    label: str
    definition: str          # key under "definitions" in the contract
    prompt_module: str       # module under worker/ that builds the prompt
    # The JSON example of ONE item, as the prompt module defines it.
    example: Callable[[ModuleType], str]
    # The generation prompt, rendered; it must embed {"<payload_key>":[<example>]}.
    render: Callable[[ModuleType], str]
    payload_key: str
    use_case: Path           # file holding the Pydantic parser
    pydantic_model: str
    stored_model: str
    # Contract fields the LLM must not supply, each naming the attribute on
    # the stored model that actually carries it. The attribute is verified to
    # exist -- an entry here is a claim about code, not a note. If a contract
    # field is neither asked of the model nor listed here, no code produces it
    # and the check says so rather than quietly subtracting it.
    code_filled: dict[str, str] = field(default_factory=dict)


_QUIZ_PROMPT = "worker.prompts.curriculum_quiz"
_QUIZ_ARGS = dict(
    course_title="C", lo_code="L", lo_vi="V", lo_en=None, bloom="b", style="quiz", count=1,
    context_parts=["x"],
)


def _quiz_spec(question_type: str, definition: str, pydantic_model: str) -> Spec:
    return Spec(
        label=f"quiz item {question_type}",
        definition=definition,
        prompt_module=_QUIZ_PROMPT,
        example=lambda m: m._KINDS[question_type].item_json,
        render=lambda m: m.generation(**_QUIZ_ARGS, question_type=question_type).user,
        payload_key="questions",
        use_case=USE_CASES / "generate_curriculum_quiz.py",
        pydantic_model=pydantic_model,
        stored_model="StoredQuizItem",
        code_filled={"model_id": "model_id"},
    )


SPECS = (
    _quiz_spec("MCQ_SINGLE", "quizItem", "_CurriculumQuestion"),
    _quiz_spec("MCQ_MULTI", "multiAnswerItem", "_MultiAnswerQuestion"),
    _quiz_spec("TRUE_FALSE", "trueFalseItem", "_TrueFalseQuestion"),
    _quiz_spec("FILL_BLANK", "fillBlankItem", "_FillBlankQuestion"),
    _quiz_spec("SHORT_ANSWER", "shortAnswerItem", "_ShortAnswerQuestion"),
    Spec(
        label="lesson card",
        definition="lessonCard",
        prompt_module="worker.prompts.lesson_cards",
        example=lambda m: m._CARD_JSON,
        render=lambda m: m.generation(
            course_title="C", lo_code="L", lo_vi="V", lo_en=None, count=1, max_bullets=4,
            context_parts=["x"],
        ).user,
        payload_key="cards",
        use_case=USE_CASES / "generate_lesson_cards.py",
        pydantic_model="_LessonCard",
        stored_model="StoredLessonCard",
        code_filled={"model_id": "model_id"},
    ),
)


def contract_fields(definition: str) -> set[str]:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return set(schema["definitions"].get(definition, {}).get("properties", {}))


def load_prompt_module(name: str) -> ModuleType:
    if str(WORKER_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKER_ROOT))
    return importlib.import_module(name)


def prompt_fields(spec: Spec) -> tuple[set[str], str | None]:
    """Field names in the JSON example of one item, and a problem if the
    generation prompt the model actually receives does not show that example."""
    module = load_prompt_module(spec.prompt_module)
    example = spec.example(module)
    try:
        fields = set(json.loads(example))
    except (ValueError, TypeError):
        return set(), "the JSON example in the prompt module is not valid JSON"
    wrapped = f'{{"{spec.payload_key}":[{example}]}}'
    if wrapped not in spec.render(module):
        return fields, (
            f"the generation prompt does not contain {wrapped[:60]}... -- the model is "
            "shown a different shape than the one checked here"
        )
    return fields, None


def class_fields(source: str, class_name: str) -> set[str]:
    """Annotated attributes of a class and of its base classes in the same
    file, via AST so a reformat or an added validator cannot fool it."""
    classes = {
        node.name: node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
    }

    def collect(name: str) -> set[str]:
        node = classes.get(name)
        if node is None:
            return set()
        own = {
            stmt.target.id
            for stmt in node.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
        }
        for base in node.bases:
            if isinstance(base, ast.Name):
                own |= collect(base.id)
        return own

    return collect(class_name)


def check_spec(spec: Spec, stored_source: str) -> list[str]:
    source = spec.use_case.read_text(encoding="utf-8")
    contract = contract_fields(spec.definition)
    prompt, wiring_problem = prompt_fields(spec)
    pydantic = class_fields(source, spec.pydantic_model)
    stored = class_fields(stored_source, spec.stored_model)
    expected = contract - set(spec.code_filled)

    problems: list[str] = [wiring_problem] if wiring_problem else []

    if not contract:
        problems.append(
            f"the contract has no definitions.{spec.definition} -- was it renamed?"
        )

    unknown = set(spec.code_filled) - contract
    if unknown and contract:
        problems.append(
            f"code_filled names {sorted(unknown)}, which the contract does not define. "
            "Either the field was renamed in the contract or the exclusion is stale."
        )

    # An exclusion has to point at an attribute that exists. Otherwise the
    # check just subtracts a field nobody produces and calls it agreement.
    for contract_field, attr in sorted(spec.code_filled.items()):
        if attr not in stored:
            problems.append(
                f"code_filled maps contract field {contract_field!r} to "
                f"{spec.stored_model}.{attr}, which does not exist. "
                f"{spec.stored_model} has {sorted(stored)}."
            )

    if not prompt:
        problems.append("could not read the JSON example in the prompt -- has its shape changed?")
    elif prompt != expected:
        missing, extra = sorted(expected - prompt), sorted(prompt - expected)
        for contract_field in list(missing):
            # Distinguish "the prompt forgot to ask" from "nothing anywhere
            # produces this" -- they need different fixes.
            if contract_field not in stored:
                missing.remove(contract_field)
                problems.append(
                    f"contract requires {contract_field!r}, but the prompt does not ask the "
                    f"model for it and no {spec.stored_model} attribute carries it. No code "
                    "produces this field; either implement it or drop it from the contract."
                )
        if missing or extra:
            problems.append(
                f"the prompt asks for {sorted(prompt)}, but the contract expects the model to "
                f"supply {sorted(expected)}."
                + (f" Never asked for: {missing}." if missing else "")
                + (f" Asked for but not in the contract: {extra}." if extra else "")
            )

    if not pydantic:
        problems.append(f"could not find class {spec.pydantic_model} -- was it renamed?")
    elif pydantic != prompt and prompt:
        missing, extra = sorted(prompt - pydantic), sorted(pydantic - prompt)
        problems.append(
            f"{spec.pydantic_model} parses {sorted(pydantic)}, but the prompt asks for "
            f"{sorted(prompt)}."
            + (f" Silently dropped: {missing}." if missing else "")
            + (f" Parsed but never asked for: {extra}." if extra else "")
        )
    return problems


def main(argv: list[str]) -> int:
    # A required CI check must fail when its input is gone, otherwise losing
    # the submodule silently turns the check into a no-op -- the failure mode
    # check_service_sdk_pins.py spent weeks in. Skipping is opt-in and loud.
    allow_missing = "--allow-missing" in argv
    for path in (*(spec.use_case for spec in SPECS), PROMPTS, STORED_MODEL_FILE):
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

    stored_source = STORED_MODEL_FILE.read_text(encoding="utf-8")
    failed = False

    # Every question type the prompt knows must have a spec, so a new type
    # cannot reach production without a contract definition.
    kinds = set(load_prompt_module(_QUIZ_PROMPT)._KINDS)
    checked = {spec.label.removeprefix("quiz item ") for spec in SPECS if spec.prompt_module == _QUIZ_PROMPT}
    if kinds != checked:
        failed = True
        print(
            "[check_content_schema] FAILED: question types in the prompt "
            f"{sorted(kinds)} differ from the types checked here {sorted(checked)}. "
            "Add a contract definition and a Spec for each new type.\n"
        )

    for spec in SPECS:
        problems = check_spec(spec, stored_source)
        if problems:
            failed = True
            print(f"[check_content_schema] FAILED ({spec.label}):\n")
            for problem in problems:
                print(f"  - {problem}\n")
            print(f"  Contract: {CONTRACT.relative_to(REPO_ROOT)} (definitions.{spec.definition})")
            print(f"  Prompt: {spec.prompt_module}")
            print(f"  Parser: {spec.use_case.relative_to(REPO_ROOT)}")
            print(f"  Persisted model: {STORED_MODEL_FILE.relative_to(REPO_ROOT)}\n")
            continue

        asked, _ = prompt_fields(spec)
        print(
            f"[check_content_schema] OK ({spec.label}) -- contract, prompt and "
            f"{spec.pydantic_model} agree on {len(asked)} LLM-supplied field(s); "
            f"{len(spec.code_filled)} filled by code:"
        )
        for contract_field, attr in sorted(spec.code_filled.items()):
            print(f"    {contract_field} <- {spec.stored_model}.{attr}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
