import logging
import re

import verifiers as vf
from datasets import load_dataset

from alignment_check import (
    _find_spans,
    _validate_box,
    detect_misaligned,
    has_disallowed_box_drawing_chars,
    normalize_grid,
)


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


def _alignment_stats(completion) -> dict[str, int] | None:
    diagram = _extract_diagram(completion)
    if diagram is None:
        return None

    if has_disallowed_box_drawing_chars(diagram):
        return None

    return detect_misaligned(diagram)


def alignment_reward(completion) -> float:
    stats = _alignment_stats(completion)
    if stats is None:
        return 0.0

    correct = stats["correct_rectangles"]
    misaligned = stats["misaligned"]

    total = correct + misaligned
    if total <= 0:
        return 0.0

    return correct / total


def _cluster_columns(columns: list[float], threshold: float = 2.0) -> list[list[float]]:
    if not columns:
        return []

    sorted_cols = sorted(columns)
    clusters: list[list[float]] = [[sorted_cols[0]]]

    for col in sorted_cols[1:]:
        cluster_center = sum(clusters[-1]) / len(clusters[-1])
        if abs(col - cluster_center) <= threshold:
            clusters[-1].append(col)
        else:
            clusters.append([col])

    return clusters


def _expected_layout_columns(info: dict | None, box_count: int) -> int:
    if box_count <= 2:
        return 2

    safe_info = info or {}
    theme = str(safe_info.get("theme", "")).lower()

    shape_budget = safe_info.get("shape_budget")
    try:
        shape_budget = int(shape_budget) if shape_budget is not None else None
    except (TypeError, ValueError):
        shape_budget = None

    if theme == "sequence":
        return 3

    if shape_budget is not None:
        if shape_budget >= 10:
            return 3
        if shape_budget <= 4:
            return 2

    if box_count >= 6:
        return 3
    return 2


def _desired_boxes_per_column(info: dict | None) -> float:
    safe_info = info or {}
    theme = str(safe_info.get("theme", "")).lower()

    shape_budget = safe_info.get("shape_budget")
    try:
        shape_budget = int(shape_budget) if shape_budget is not None else None
    except (TypeError, ValueError):
        shape_budget = None

    if theme == "sequence":
        return 1.6
    if theme == "state_machines":
        return 2.0 if shape_budget is not None and shape_budget >= 12 else 2.3
    if shape_budget is not None and shape_budget >= 12:
        return 2.2
    return 2.8


def _layout_box_centers(grid: list[list[str]]) -> list[float]:
    if not grid:
        return []

    top_spans = sorted(_find_spans(grid, "┌", "┐"), key=lambda s: (s.row, s.c0, s.c1))
    bottom_spans = sorted(_find_spans(grid, "└", "┘"), key=lambda s: (s.row, s.c0, s.c1))

    bottoms_by_key: dict[tuple[int, int], list] = {}
    for bottom in bottom_spans:
        bottoms_by_key.setdefault((bottom.c0, bottom.c1), []).append(bottom)

    centers: list[float] = []
    for top in top_spans:
        candidates = bottoms_by_key.get((top.c0, top.c1), [])
        for bottom in candidates:
            if bottom.row <= top.row:
                continue
            if _validate_box(grid, top, bottom):
                centers.append(0.5 * (top.c0 + top.c1))
                break

    return centers


def layout_spread_reward(completion, info=None) -> float:
    diagram = _extract_diagram(completion)
    if diagram is None:
        return 0.0

    if has_disallowed_box_drawing_chars(diagram):
        return 0.0

    grid = normalize_grid(diagram)
    if not grid or not grid[0]:
        return 0.0

    centers = _layout_box_centers(grid)
    box_count = len(centers)
    if box_count < 2:
        return 0.0

    clusters = _cluster_columns(centers, threshold=2.0)
    unique_columns = len(clusters)

    expected_columns = _expected_layout_columns(info, box_count)
    column_score = min(1.0, max(0.0, (unique_columns - 1) / max(1, expected_columns - 1)))

    width = len(grid[0])
    horizontal_span = max(centers) - min(centers)
    normalized_span = horizontal_span / max(1.0, float(width - 1))
    span_target = 0.22 if expected_columns >= 3 else 0.12
    span_score = min(1.0, normalized_span / span_target)

    largest_cluster = max(len(cluster) for cluster in clusters)
    dominance = largest_cluster / float(box_count)
    stack_penalty = 0.0 if unique_columns == 1 else (0.75 if dominance >= 0.85 and box_count >= 4 else 1.0)

    boxes_per_column = box_count / float(unique_columns)
    desired_bpc = _desired_boxes_per_column(info)
    column_density_penalty = min(1.0, desired_bpc / max(1.0, boxes_per_column))

    score = (0.7 * column_score + 0.3 * span_score) * stack_penalty * column_density_penalty
    return max(0.0, min(1.0, score))


def _alignment_total(stats: dict[str, int] | None) -> float:
    if stats is None:
        return 0.0
    correct = float(stats["correct_rectangles"])
    misaligned = float(stats["misaligned"])
    total = correct + misaligned
    if total <= 0.0:
        return 0.0
    return total


def _normalized_dimension(stats: dict[str, int] | None, key: str) -> float:
    total = _alignment_total(stats)
    if total <= 0.0:
        return 0.0
    return float(stats[key]) / total


def rectangle_error_metric(completion) -> float:
    stats = _alignment_stats(completion)
    return _normalized_dimension(stats, "rectangle_errors")


def connector_error_metric(completion) -> float:
    stats = _alignment_stats(completion)
    return _normalized_dimension(stats, "connector_errors")


def arrow_error_metric(completion) -> float:
    stats = _alignment_stats(completion)
    return _normalized_dimension(stats, "arrow_errors")


def misaligned_total_metric(completion) -> float:
    stats = _alignment_stats(completion)
    return _normalized_dimension(stats, "misaligned")


def load_environment() -> vf.Environment:
    """
    Single-turn environment that asks for ASCII diagrams inside ```text fences.
    """
    dataset = load_dataset("13point5/tldraw-vf-env", split="train")

    # Keep a stable ID tied to original dataset row order.
    dataset = dataset.map(lambda _row, idx: {"source_index": idx}, with_indices=True)

    # convert prompt into an array with one user message object
    dataset = dataset.map(lambda row: {"prompt": [{"role": "user", "content": row["prompt"]}]})

    columns = dataset.column_names
    dataset = dataset.map(lambda row: {"info": dict(row)})

    columns_to_remove = [col for col in columns if col not in ["prompt", "info"]]
    dataset = dataset.remove_columns(columns_to_remove)

    split = dataset.train_test_split(test_size=0.2, seed=42, shuffle=True)
    train_dataset = split["train"]
    eval_dataset = split["test"]

    # Track final train ordering so runs/resumes can be compared in the web app.
    train_dataset = train_dataset.map(
        lambda row, idx: {
            "info": {
                **dict(row["info"]),
                "source_index": row["info"]["source_index"],
                "train_order_index": idx,
            }
        },
        with_indices=True,
    )

    rubric = vf.Rubric(
        funcs=[
            format_reward,
            alignment_reward,
            layout_spread_reward,
            rectangle_error_metric,
            connector_error_metric,
            arrow_error_metric,
            misaligned_total_metric,
        ],
        weights=[1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    )

    return vf.SingleTurnEnv(
        dataset=train_dataset,
        eval_dataset=eval_dataset,
        system_prompt=SYSTEM_PROMPT,
        rubric=rubric,
    )
