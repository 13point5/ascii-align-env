from alignment_check import detect_misaligned


def test_orphan_left_arrow_tail_corner_invalid() -> None:
    diagram = """\
┌───────────┐
│  Node     │◄───┘
└───────────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_dangling_down_arrow_no_end_invalid() -> None:
    diagram = """\
┌───────────┐
│  Start    │
└───────────┘
     │
     ▼
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_dangling_up_arrow_no_start_invalid() -> None:
    diagram = """\
     ▲
     │
┌───────────┐
│  End      │
└───────────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_mixed_valid_and_shifted_box_rows_invalid() -> None:
    diagram = """\
┌───────────┐
│  Good     │
└───────────┘

┌───────────┐
 │  Bad A    │
 │  Bad B    │
 └───────────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["correct_rectangles"] >= 1
    assert stats["rectangle_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_vertical_stack_off_center_connector_invalid() -> None:
    diagram = """\
┌─────────┐
│ Stage A │
└─────────┘
    │
    ▼
┌─────────┐
│ Stage B │
└─────────┘
    │
    ▼
┌─────────┐
│ Stage C │
└─────────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_vertical_stack_centered_connector_valid() -> None:
    diagram = """\
┌─────────┐
│ Stage A │
└─────────┘
     │
     ▼
┌─────────┐
│ Stage B │
└─────────┘
     │
     ▼
┌─────────┐
│ Stage C │
└─────────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 0
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_unicode_pointer_arrow_variants_supported() -> None:
    diagrams = [
        """\
┌────┐   ┌────┐
│ A  │──►│ B  │
└────┘   └────┘
""",
        """\
┌────┐   ┌────┐
│ A  │◄──│ B  │
└────┘   └────┘
""",
    ]
    for diagram in diagrams:
        stats = detect_misaligned(diagram, require_at_least_one_rect=False)
        assert stats["arrow_errors"] == 0
        assert stats["misaligned"] == 0
