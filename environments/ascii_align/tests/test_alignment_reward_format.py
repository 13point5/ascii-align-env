import sys
import types


if "verifiers" not in sys.modules:
    sys.modules["verifiers"] = types.SimpleNamespace(Environment=object, Rubric=object, SingleTurnEnv=object)
if "datasets" not in sys.modules:
    sys.modules["datasets"] = types.SimpleNamespace(load_dataset=lambda *args, **kwargs: None)

from ascii_align import alignment_reward, format_reward


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
