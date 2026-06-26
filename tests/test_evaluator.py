from __future__ import annotations

import pytest

from noctra_browser.runtime.evaluator import RuntimeEvaluator


@pytest.fixture
def evaluator() -> RuntimeEvaluator:
    return RuntimeEvaluator(session=None)  # type: ignore[arg-type]


def test_plain_expression_is_passed_through(evaluator: RuntimeEvaluator) -> None:
    assert evaluator._wrap_expression("2 * 21", ()) == "2 * 21"


def test_expression_with_arrow_in_method_call_is_not_wrapped(
    evaluator: RuntimeEvaluator,
) -> None:
    # "[1].map(x => x)" contains "=>" but is an expression, not a callable source.
    assert evaluator._wrap_expression("[1,2,3].map(x => x * 2)", ()) == "[1,2,3].map(x => x * 2)"


def test_arrow_function_source_is_invoked(evaluator: RuntimeEvaluator) -> None:
    wrapped = evaluator._wrap_expression("() => ({a: 1})", ())
    assert "__noctra_v" in wrapped
    assert "typeof __noctra_v === 'function'" in wrapped


def test_function_with_args_is_invoked_with_them(evaluator: RuntimeEvaluator) -> None:
    wrapped = evaluator._wrap_expression("(a, b) => a + b", (3, 4))
    assert "[3,4]" in wrapped
    assert "__noctra_v(...[3,4])" in wrapped


def test_already_invoked_iife_is_not_double_called(evaluator: RuntimeEvaluator) -> None:
    # The typeof guard means even if wrapped, an IIFE result is returned as-is.
    wrapped = evaluator._wrap_expression("(() => 99)()", ())
    assert "typeof __noctra_v === 'function'" in wrapped


@pytest.mark.parametrize(
    "source",
    ["function () { return 1; }", "async function () {}", "() => 1", "async () => 1"],
)
def test_function_shapes_are_detected(evaluator: RuntimeEvaluator, source: str) -> None:
    assert evaluator._looks_like_function(source) is True


@pytest.mark.parametrize("source", ["1 + 1", "document.title", "[1].map(x => x)"])
def test_non_function_shapes_are_not_detected(
    evaluator: RuntimeEvaluator, source: str
) -> None:
    assert evaluator._looks_like_function(source) is False
