import re
import logging

import verifiers as vf
from datasets import Dataset

from data import get_default_prompts
from alignment_check import detect_misaligned


logger = logging.getLogger("verifiers.ascii_align")

_TEXT_FENCE_RE = re.compile(r"```text\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """
You generate ASCII diagrams for the user's request. 
Respond with a single markdown code block fenced with ```text and ``` 
containing only the ASCII diagram.

Only use these characters for boxes: ┌, ┐, └, ┘, ├, ┤, ┬, ┴, ┼, ─, │.
"""


def _extract_diagram(completion) -> str | None:
    response = completion[-1]["content"]

    match = _TEXT_FENCE_RE.search(response)
    if not match:
        return None

    diagram = match.group(1).strip("\n")
    if not diagram.strip():
        return None

    return diagram


def format_reward(completion) -> float:
    diagram = _extract_diagram(completion)
    if diagram is None:
        return 0.0
    return 1.0


def alignment_reward(completion) -> float:
    diagram = _extract_diagram(completion)
    if diagram is None:
        return 0.0

    stats = detect_misaligned(diagram)
    correct = stats["correct"]
    misaligned = stats["misaligned"]

    total = correct + misaligned
    if total <= 0:
        return 0.0

    return correct / total


def load_environment() -> vf.Environment:
    """
    Single-turn environment that asks for ASCII diagrams inside ```text fences.
    """

    default_prompts = get_default_prompts()
    dataset = Dataset.from_list([{"question": prompt} for prompt in default_prompts])

    rubric = vf.Rubric(funcs=[format_reward, alignment_reward])

    return vf.SingleTurnEnv(
        dataset=dataset,
        system_prompt=SYSTEM_PROMPT,
        rubric=rubric,
    )
