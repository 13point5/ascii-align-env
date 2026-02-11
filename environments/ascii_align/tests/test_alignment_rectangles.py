import pytest

from alignment_check import detect_misaligned
from cases import CASE_SPECS


RECT_CASES = [
    (
        "rect_empty_input",
        "",
    ),
    (
        "rect_whitespace_only",
        "   \n\t",
    ),
    (
        "rect_single_valid_box",
        """\
┌─────┐
│ A   │
└─────┘
""",
    ),
    (
        "rect_two_valid_side_by_side",
        """\
┌────┐  ┌────┐
│ A  │  │ B  │
└────┘  └────┘
""",
    ),
    (
        "rect_nested_valid",
        """\
┌─────────┐
│ ┌─────┐ │
│ │ X   │ │
│ └─────┘ │
└─────────┘
""",
    ),
    (
        "rect_missing_bottom_right_corner",
        """\
┌─────┐
│ A   │
└─────
""",
    ),
    (
        "rect_right_edge_shifted",
        """\
┌─────┐
│ A   │
 └────┘
""",
    ),
    (
        "rect_top_edge_gap",
        """\
┌── ──┐
│ A   │
└─────┘
""",
    ),
    (
        "rect_mixed_one_valid_one_invalid",
        """\
┌────┐  ┌────┐
│ A  │  │ B  │
└────┘  └───┘
""",
    ),
    (
        "rect_no_rectangle_text_only",
        """\
hello world
no boxes
""",
    ),
]


def _assert_expected(case_name: str, stats: dict) -> None:
    expected = CASE_SPECS[case_name]["expected"]
    for key, value in expected.items():
        assert stats[key] == value, f"{case_name} expected {key}={value}, got {stats[key]}"


@pytest.mark.parametrize("case_name,diagram", RECT_CASES)
def test_rectangle_cases(case_name: str, diagram: str) -> None:
    stats = detect_misaligned(diagram)
    _assert_expected(case_name, stats)

