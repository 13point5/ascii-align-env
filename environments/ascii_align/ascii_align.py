import logging
import re

import verifiers as vf
from datasets import load_dataset

from alignment_check import detect_misaligned, has_disallowed_box_drawing_chars


logger = logging.getLogger("verifiers.ascii_align")

_TEXT_FENCE_RE = re.compile(r"```text\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """
You generate ASCII diagrams for the user's request. 
Respond with a single markdown code block fenced with ```text and ``` 
containing only the ASCII diagram.

For box structure, use only these corner characters: ┌, ┐, └, ┘.
For box edges and junctions, use only: ─, │, ├, ┤, ┬, ┴, ┼.
You may use normal text/content characters (letters, numbers, punctuation, symbols) for labels.
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

    if has_disallowed_box_drawing_chars(diagram):
        return 0.0

    stats = detect_misaligned(diagram)
    correct = stats["correct_rectangles"]
    misaligned = stats["misaligned"]

    total = correct + misaligned
    if total <= 0:
        return 0.0

    return correct / total


def load_environment() -> vf.Environment:
    """
    Single-turn environment that asks for ASCII diagrams inside ```text fences.
    """

    dataset = load_dataset("13point5/tldraw-vf-env", split="train")

    # convert prompt into an array with one user message object
    dataset = dataset.map(lambda row: {"prompt": [{"role": "user", "content": row["prompt"]}]})

    columns = dataset.column_names
    dataset = dataset.map(lambda row: {"info": dict(row)})

    columns_to_remove = [col for col in columns if col not in ["prompt", "info"]]
    dataset = dataset.remove_columns(columns_to_remove)

    split = dataset.train_test_split(test_size=0.2, seed=42, shuffle=True)
    train_dataset = split["train"]
    eval_dataset = split["test"]

    rubric = vf.Rubric(funcs=[format_reward, alignment_reward])

    return vf.SingleTurnEnv(
        dataset=train_dataset,
        eval_dataset=eval_dataset,
        system_prompt=SYSTEM_PROMPT,
        rubric=rubric,
    )
