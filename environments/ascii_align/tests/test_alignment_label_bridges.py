from alignment_check import detect_misaligned


def test_label_bridge_horizontal_valid() -> None:
    diagram = """\
┌────┐        ┌────┐
│ A  │─ ok ──▶│ B  │
└────┘        └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 0
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_label_bridge_missing_left_line() -> None:
    diagram = """\
┌────┐        ┌────┐
│ A  │  ok ──▶│ B  │
└────┘        └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_label_bridge_missing_right_line() -> None:
    diagram = """\
┌────┐        ┌────┐
│ A  │── ok   ▶│ B  │
└────┘        └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_label_bridge_text_but_no_resume_before_arrow() -> None:
    diagram = """\
┌────┐        ┌────┐
│ A  │── ok   ▶│ B  │
└────┘        └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 2


def test_label_bridge_spaces_only_invalid() -> None:
    diagram = """\
┌────┐        ┌────┐
│ A  │──    ──▶│ B  │
└────┘        └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_label_bridge_punctuation_valid() -> None:
    diagram = """\
┌────┐          ┌────┐
│ A  │─ ok!? ──▶│ B  │
└────┘          └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 0
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_label_vertical_near_line_not_bridge_but_valid_line() -> None:
    diagram = """\
┌──┐
│A │
└┬─┘
 Pass
  │
  ▼
┌──┐
│B │
└──┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["misaligned"] == 0


def test_label_interrupts_vertical_line_invalid() -> None:
    diagram = """\
  │
  X
  │
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_label_overlap_with_malformed_box() -> None:
    diagram = """\
┌──────┐
│ A ok │
└─────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["rectangle_errors"] >= 1
    assert stats["misaligned"] >= 1
