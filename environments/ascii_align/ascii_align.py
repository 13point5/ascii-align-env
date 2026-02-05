import re
import logging

import verifiers as vf
from datasets import Dataset

from data import get_default_prompts


logger = logging.getLogger("verifiers.ascii_align")

DEFAULT_SYSTEM_PROMPT = """
You generate ASCII diagrams for the user's request. 
Respond with a single markdown code block fenced with ```text and ``` 
containing only the ASCII diagram.

Only use these characters for boxes: ┌, ┐, └, ┘, ├, ┤, ┬, ┴, ┼, ─, │.
"""


_TEXT_FENCE_RE = re.compile(r"```text\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def format_reward(completion) -> float:
    response = completion[-1]["content"]
    match = _TEXT_FENCE_RE.search(response)
    if not match:
        return 0.0

    diagram = match.group(1).strip("\n")

    if not diagram.strip():
        return 0.0

    return 1.0


def load_environment() -> vf.Environment:
    """
    Single-turn environment that asks for ASCII diagrams inside ```text fences.
    """

    default_prompts = get_default_prompts()
    dataset = Dataset.from_list([{"question": prompt} for prompt in default_prompts])

    rubric = vf.Rubric(funcs=[format_reward])

    return vf.SingleTurnEnv(
        dataset=dataset,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        rubric=rubric,
    )
