import sys
import types

import pytest


if "verifiers" not in sys.modules:
    sys.modules["verifiers"] = types.SimpleNamespace(Environment=object, Rubric=object, SingleTurnEnv=object)
if "datasets" not in sys.modules:
    sys.modules["datasets"] = types.SimpleNamespace(load_dataset=lambda *args, **kwargs: None)

from ascii_align import (
    alignment_reward,
    arrow_error_metric,
    connector_error_metric,
    format_reward,
    misaligned_total_metric,
    rectangle_error_metric,
)


def _completion(content: str) -> list[dict[str, str]]:
    return [{"role": "assistant", "content": content}]


def test_format_missing_text_fence() -> None:
    reward = format_reward(_completion("not fenced"))
    assert reward == 0.0


def test_format_empty_text_fence() -> None:
    reward = format_reward(_completion("```text\n\n```"))
    assert reward == 0.0


def test_chars_disallowed_rounded_corners() -> None:
    response = """```text
╭───╮
│ A │
╰───╯
```"""
    reward = alignment_reward(_completion(response))
    assert reward == 0.0


def test_chars_allowed_content_symbols() -> None:
    response = """```text
┌─────────┐
│ Ops#1!? │
└─────────┘
```"""
    reward = alignment_reward(_completion(response))
    assert reward > 0.0


def test_metric_rectangle_errors_dimension() -> None:
    response = """```text
┌─────┐
│ A   │
 └────┘
    ```"""
    completion = _completion(response)
    assert rectangle_error_metric(completion) == 1.0
    assert connector_error_metric(completion) == 0.0
    assert arrow_error_metric(completion) == 0.0
    assert misaligned_total_metric(completion) == 1.0


def test_metric_connector_errors_dimension() -> None:
    response = """```text
┌─┐
│ │
└─┘
  │
  │
    ```"""
    completion = _completion(response)
    assert rectangle_error_metric(completion) == 0.0
    assert connector_error_metric(completion) == pytest.approx(0.5)
    assert arrow_error_metric(completion) == 0.0
    assert misaligned_total_metric(completion) == pytest.approx(0.5)


def test_metric_arrow_errors_dimension() -> None:
    response = """```text
┌────┐   ┌────┐
│ A  │  ▶│ B  │
└────┘   └────┘
    ```"""
    completion = _completion(response)
    assert rectangle_error_metric(completion) == 0.0
    assert connector_error_metric(completion) == 0.0
    assert arrow_error_metric(completion) == pytest.approx(1.0 / 3.0)
    assert misaligned_total_metric(completion) == pytest.approx(1.0 / 3.0)
