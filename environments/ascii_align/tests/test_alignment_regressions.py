from alignment_check import detect_misaligned
from cases import CASE_SPECS


USER_FLOWCHART_CASE = """\
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ API         │────▶│ Approval    │────▶│ Transcoding │
│ Gateway     │     │ Service     │     │ Service     │
└─────────────┘     └─────────────┘     └─────────────┘
      ▲                    ▲                    ▲
      │                    │                    │
      │ Reject             │ Approve            │ Failure
      ▼                    ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Notification│◀────│ Review      │◀────│ Notify      │
│ Service     │     │ Step        │     │ Failure     │
└─────────────┘     └─────────────┘     └─────────────┘
"""

USER_SEQUENCE_CASE = """\
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Queue   │────▶│ Worker  │────▶│Reviewer │────▶│Storage  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     ▲                ▲                ▲                ▲
     │                │                │                │
     └────────────────┴────────────────┴────────────────┴────────────────┐
                                                                        │
                                                                        ▼
┌─────────┐     ┌─────────┐     ┌─────────┐                              │
│Restore  │◄────┤Handler  │◄────┤Checker  │                              │
└─────────┘     └─────────┘     └─────────┘                              │
                                                                        │
                                                                        ▼
                                                  Handles empty/corrupted backups
"""


def _policy_diagram_lines() -> list[str]:
    return [
        "┌─────────────┐     ┌──────────────┐     ┌─────────────┐",
        "│ API         │────▶│ Authorization│────▶│ Data        │",
        "│ Gateway     │     │ Check        │     │ Schema      │",
        "└─────────────┘     └──────────────┘     └─────────────┘",
        "      │                   │                   │",
        "      │ Fail              │ Fail              │ Fail",
        "      ▼                   ▼                   ▼",
        "┌─────────────┐     ┌──────────────┐     ┌─────────────┐",
        "│ Error       │     │ Error        │     │ Error       │",
        "│ Response    │     │ Response     │     │ Response    │",
        "└─────────────┘     └──────────────┘     └─────────────┘",
        "      │                   │                   │",
        "      └───────────────────┴───────────────────┘",
        "                        Pass",
        "                         │",
        "                         ▼",
        "┌─────────────┐     ┌──────────────┐     ┌─────────────┐",
        "│ Content     │────▶│ Queue        │────▶│ Worker      │",
        "│ Filter      │     │ Notification │     │ Service     │",
        "└─────────────┘     └──────────────┘     └─────────────┘",
        "      │                   │                   │",
        "      │ Prohibited        │                   ▼",
        "┌─────────────┐          │             ┌─────────────┐",
        "│ Error       │          │             │ Logging     │",
        "│ Response    │          │             │ & Monitoring",
        "└─────────────┘          │             └─────────────┘",
    ]


def _policy_current() -> str:
    return "\n".join(_policy_diagram_lines())


def _policy_fix_dangling_queue_line() -> str:
    lines = _policy_diagram_lines()
    for idx in [20, 21, 22, 23, 24, 25]:
        chars = list(lines[idx])
        for col, ch in enumerate(chars):
            if ch == "│" and 18 < col < 35:
                chars[col] = " "
                break
        lines[idx] = "".join(chars)
    return "\n".join(lines)


def _policy_fix_logging_box_only() -> str:
    lines = _policy_diagram_lines()
    lines[24] = "│ Response    │          │             │ & Monitoring│"
    return "\n".join(lines)


def _policy_fix_all() -> str:
    lines = _policy_diagram_lines()
    for idx in [20, 21, 22, 23, 24, 25]:
        chars = list(lines[idx])
        for col, ch in enumerate(chars):
            if ch == "│" and 18 < col < 35:
                chars[col] = " "
                break
        lines[idx] = "".join(chars)
    lines[24] = "│ Response    │                        │ & Monitoring│"
    return "\n".join(lines)


def test_regression_user_flowchart_case() -> None:
    stats = detect_misaligned(USER_FLOWCHART_CASE)
    expected = CASE_SPECS["regression_user_flowchart_case"]["expected"]
    assert stats["misaligned"] >= expected["misaligned_min"]
    assert stats["connector_errors"] >= expected["connector_errors_min"]


def test_regression_user_sequence_case() -> None:
    stats = detect_misaligned(USER_SEQUENCE_CASE)
    expected = CASE_SPECS["regression_user_sequence_case"]["expected"]
    assert stats["misaligned"] >= expected["misaligned_min"]
    assert stats["connector_errors"] >= expected["connector_errors_min"]


def test_regression_policy_diagram_current() -> None:
    stats = detect_misaligned(_policy_current())
    expected = CASE_SPECS["regression_policy_diagram_current"]["expected"]
    for key, value in expected.items():
        assert stats[key] == value, f"expected {key}={value}, got {stats[key]}"


def test_regression_policy_diagram_fix_dangling_queue_line() -> None:
    stats = detect_misaligned(_policy_fix_dangling_queue_line())
    expected = CASE_SPECS["regression_policy_diagram_fix_dangling_queue_line"]["expected"]
    for key, value in expected.items():
        assert stats[key] == value, f"expected {key}={value}, got {stats[key]}"


def test_regression_policy_diagram_fix_logging_box_only() -> None:
    stats = detect_misaligned(_policy_fix_logging_box_only())
    expected = CASE_SPECS["regression_policy_diagram_fix_logging_box_only"]["expected"]
    for key, value in expected.items():
        assert stats[key] == value, f"expected {key}={value}, got {stats[key]}"


def test_regression_policy_diagram_fix_all() -> None:
    stats = detect_misaligned(_policy_fix_all())
    expected = CASE_SPECS["regression_policy_diagram_fix_all"]["expected"]
    for key, value in expected.items():
        assert stats[key] == value, f"expected {key}={value}, got {stats[key]}"


def test_ansi_colored_valid_diagram_matches_uncolored() -> None:
    base = """\
┌────┐   ┌────┐
│ A  │──▶│ B  │
└────┘   └────┘
"""
    colored = (
        "\x1b[35m┌────┐\x1b[0m   \x1b[35m┌────┐\x1b[0m\n"
        "\x1b[35m│ A  │\x1b[0m──▶\x1b[35m│ B  │\x1b[0m\n"
        "\x1b[35m└────┘\x1b[0m   \x1b[35m└────┘\x1b[0m\n"
    )
    assert detect_misaligned(base) == detect_misaligned(colored)

