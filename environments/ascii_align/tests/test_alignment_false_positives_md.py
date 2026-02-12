from __future__ import annotations

from pathlib import Path
import re

import pytest

from alignment_check import detect_misaligned


_FALSE_POS_DIR = Path(__file__).parent / "false-positives"
_CODE_BLOCK_RE = re.compile(r"```text\n(.*?)\n```", re.S)

EXPECTED = {
    "01.md": {
        "correct_rectangles": 4,
        "rectangle_errors": 6,
        "connector_errors": 2,
        "arrow_errors": 0,
        "misaligned": 8,
    },
    "02.md": {
        "correct_rectangles": 11,
        "rectangle_errors": 0,
        "connector_errors": 6,
        "arrow_errors": 1,
        "misaligned": 7,
    },
    "03.md": {
        "correct_rectangles": 6,
        "rectangle_errors": 0,
        "connector_errors": 5,
        "arrow_errors": 0,
        "misaligned": 5,
    },
}


def _load_diagram(path: Path) -> str:
    text = path.read_text()
    match = _CODE_BLOCK_RE.search(text)
    assert match is not None, f"missing ```text fenced block in {path.name}"
    return match.group(1)


@pytest.mark.parametrize("filename", sorted(EXPECTED))
def test_false_positive_markdown_fixtures(filename: str) -> None:
    diagram = _load_diagram(_FALSE_POS_DIR / filename)
    stats = detect_misaligned(diagram)

    expected = EXPECTED[filename]
    for key, value in expected.items():
        assert stats[key] == value, f"{filename} expected {key}={value}, got {stats[key]}"


def test_false_positive_03_send_notification_and_notification_service_edges() -> None:
    diagram = _load_diagram(_FALSE_POS_DIR / "03.md")
    stats = detect_misaligned(diagram)

    # This fixture is a long single-column stack whose connector track drifts
    # off the geometric center of each box.
    assert stats["connector_errors"] >= 2
    assert stats["misaligned"] >= 1
