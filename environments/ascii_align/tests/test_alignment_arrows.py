from alignment_check import detect_misaligned


def test_arrow_right_valid_incoming_from_left() -> None:
    diagram = """\
┌────┐   ┌────┐
│ A  │──▶│ B  │
└────┘   └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_arrow_right_missing_incoming() -> None:
    diagram = """\
┌────┐   ┌────┐
│ A  │  ▶│ B  │
└────┘   └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 1
    assert stats["misaligned"] >= 1


def test_arrow_right_wrong_incoming_side() -> None:
    diagram = """\
┌────┐   ┌────┐
│ A  │▶──│ B  │
└────┘   └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 1
    assert stats["misaligned"] >= 1


def test_arrow_left_valid_incoming_from_right() -> None:
    diagram = """\
┌────┐   ┌────┐
│ A  │◀──│ B  │
└────┘   └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_arrow_up_valid_incoming_from_below() -> None:
    diagram = """\
┌────┐
│ A  │
└────┘
  ▲
  │
┌────┐
│ B  │
└────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_arrow_down_valid_incoming_from_above() -> None:
    diagram = """\
┌────┐
│ A  │
└─┬──┘
  │
  ▼
┌────┐
│ B  │
└────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 0
    assert stats["misaligned"] == 0


def test_arrow_ascii_variants_supported() -> None:
    diagrams = [
        "┌──────┐\n│      │\n│──>   │\n│      │\n└──────┘",
        "┌──────┐\n│      │\n│   <──│\n│      │\n└──────┘",
        "┌────┐\n│ ^  │\n│ │  │\n└────┘",
        "┌────┐\n│ │  │\n│ v  │\n└────┘",
    ]
    for diagram in diagrams:
        stats = detect_misaligned(diagram, require_at_least_one_rect=False)
        assert stats["arrow_errors"] == 0, f"ASCII arrow failed: {diagram!r} -> {stats}"


def test_arrow_multiple_incoming_invalid() -> None:
    diagram = """\
┌───┐
│ │ │
│─▶─│
└───┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] == 1
    assert stats["misaligned"] >= 1
