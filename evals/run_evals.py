"""
Evaluation harness for common assistant scenarios.

Run with:
    python3 -m evals.run_evals
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json

from agents.master_agent import MasterAgent
from config.settings import debug_print


@dataclass
class EvalCase:
    """Represents a single evaluation scenario."""

    name: str
    prompt: str
    description: str
    must_contain: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    min_length: int = 0


@dataclass
class EvalResult:
    name: str
    passed: bool
    response: str
    failures: List[str]


def _validate_response(case: EvalCase, response: str) -> List[str]:
    """Return a list of failure reasons, empty if the response passes."""
    failures: List[str] = []

    if case.min_length and len(response.strip()) < case.min_length:
        failures.append(f"response too short ({len(response.strip())} chars < {case.min_length})")

    lowered_response = response.lower()
    for token in case.must_contain:
        if token.lower() not in lowered_response:
            failures.append(f"missing expected token '{token}'")

    for token in case.must_not_contain:
        if token.lower() in lowered_response:
            failures.append(f"unexpected token '{token}' present")

    return failures


async def _run_case(case: EvalCase) -> EvalResult:
    """Run a single evaluation case with a fresh MasterAgent instance."""
    master = MasterAgent()
    debug_print(f"Running eval case '{case.name}' with prompt: {case.prompt}")
    response = await master.process(case.prompt)
    failures = _validate_response(case, response)
    return EvalResult(
        name=case.name,
        passed=not failures,
        response=response,
        failures=failures,
    )


async def run_all_evals(cases: List[EvalCase]) -> List[EvalResult]:
    """Execute evaluation cases sequentially."""
    results: List[EvalResult] = []
    for case in cases:
        result = await _run_case(case)
        results.append(result)
    return results


def _print_summary(results: List[EvalResult]) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\nEvaluation Summary: {passed}/{total} cases passed.")
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status} :: {result.name}")
        print(f"Prompt: {result.response[:120]}{'...' if len(result.response) > 120 else ''}")
        if not result.passed:
            print("Reasons:")
            for failure in result.failures:
                print(f"  - {failure}")


def load_case_definitions() -> List[EvalCase]:
    case_path = Path(__file__).with_name("cases.json")
    if case_path.exists():
        with open(case_path, "r") as handle:
            raw_cases = json.load(handle)
        cases: List[EvalCase] = []
        for raw in raw_cases:
            cases.append(
                EvalCase(
                    name=raw["name"],
                    prompt=raw["prompt"],
                    description=raw.get("description", ""),
                    must_contain=raw.get("expect_contains", []),
                    must_not_contain=raw.get("forbid_contains", []),
                    min_length=raw.get("min_length", 0),
                )
            )
        return cases
    # Fallback defaults
    return [
        EvalCase(
            name="personal_memory_name",
            prompt="What is my name?",
            description="Ensure the assistant recalls Danny's name from memory.",
            must_contain=["Danny"],
            min_length=10,
        ),
        EvalCase(
            name="search_routing",
            prompt="Search for me online",
            description="Ensure the assistant attempts an online search instead of declining.",
            must_not_contain=["can't browse the internet", "cannot browse"],
            min_length=20,
        ),
        EvalCase(
            name="help_command",
            prompt="help",
            description="Validate help command surfaces instructions.",
            must_contain=["Available Commands"],
            min_length=20,
        ),
    ]


async def main(custom_cases: Optional[List[EvalCase]] = None) -> None:
    cases = custom_cases or load_case_definitions()
    results = await run_all_evals(cases)
    _print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
