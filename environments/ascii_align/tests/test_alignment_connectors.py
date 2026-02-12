import itertools

import pytest

from alignment_check import DIR_MAP, E, N, S, W, connected, detect_misaligned, normalize_grid


H_LEFT = {ch for ch, d in DIR_MAP.items() if d & E}
H_RIGHT = {ch for ch, d in DIR_MAP.items() if d & W}
V_TOP = {ch for ch, d in DIR_MAP.items() if d & S}
V_BOTTOM = {ch for ch, d in DIR_MAP.items() if d & N}


def _horizontal_pair_diagram(left: str, right: str) -> str:
    return f"┌──┐\n│{left}{right}│\n└──┘"


def _vertical_pair_diagram(top: str, bottom: str) -> str:
    return f"┌─┐\n│{top}│\n│{bottom}│\n└─┘"


def test_mutual_horizontal_valid_matrix_49_cases() -> None:
    valid_pairs = list(itertools.product(sorted(H_LEFT), sorted(H_RIGHT)))
    assert len(valid_pairs) == 49

    for left, right in valid_pairs:
        grid = normalize_grid(_horizontal_pair_diagram(left, right))
        assert connected(grid, 1, 1, 0, 1), f"valid horizontal pair failed: {left}{right}"


def test_mutual_horizontal_invalid_matrix_72_cases() -> None:
    all_pairs = list(itertools.product(sorted(DIR_MAP), sorted(DIR_MAP)))
    invalid_pairs = [(l, r) for l, r in all_pairs if (l not in H_LEFT) or (r not in H_RIGHT)]
    assert len(invalid_pairs) == 72

    for left, right in invalid_pairs:
        grid = normalize_grid(_horizontal_pair_diagram(left, right))
        assert not connected(grid, 1, 1, 0, 1), f"invalid horizontal pair passed: {left}{right}"


def test_mutual_vertical_valid_matrix_49_cases() -> None:
    valid_pairs = list(itertools.product(sorted(V_TOP), sorted(V_BOTTOM)))
    assert len(valid_pairs) == 49

    for top, bottom in valid_pairs:
        grid = normalize_grid(_vertical_pair_diagram(top, bottom))
        assert connected(grid, 1, 1, 1, 0), f"valid vertical pair failed: {top}/{bottom}"


def test_mutual_vertical_invalid_matrix_72_cases() -> None:
    all_pairs = list(itertools.product(sorted(DIR_MAP), sorted(DIR_MAP)))
    invalid_pairs = [(t, b) for t, b in all_pairs if (t not in V_TOP) or (b not in V_BOTTOM)]
    assert len(invalid_pairs) == 72

    for top, bottom in invalid_pairs:
        grid = normalize_grid(_vertical_pair_diagram(top, bottom))
        assert not connected(grid, 1, 1, 1, 0), f"invalid vertical pair passed: {top}/{bottom}"


def test_conn_dangling_vertical_run() -> None:
    diagram = """\
┌─┐
│ │
└─┘
  │
  │
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 1
    assert stats["misaligned"] == 1


def test_conn_dangling_horizontal_run() -> None:
    diagram = """\
┌──┐
│ A│──
└──┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 1
    assert stats["misaligned"] == 1


def test_conn_broken_horizontal_gap() -> None:
    diagram = """\
┌──┐      ┌──┐
│ A│─  ──▶│ B│
└──┘      └──┘
    """
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["connector_errors"] == 1
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_conn_broken_vertical_gap() -> None:
    diagram = """\
┌─┐
│A│
└┬┘
   
 │
 ▼
┌─┐
│B│
└─┘
    """
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] >= 1 or stats["connector_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_conn_valid_t_junction() -> None:
    diagram = """\
┌───┐
│─┬─│
│ │ │
└───┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["misaligned"] == 0


def test_conn_valid_cross_junction() -> None:
    diagram = """\
┌───┐
│─┼─│
│ │ │
└───┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["misaligned"] == 0


def test_conn_attach_plain_vertical_wall_dangling_arrow_invalid() -> None:
    diagram = """\
┌────┐
│ A  │
└────┘
  │
  ▼
    """
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["arrow_errors"] >= 1
    assert stats["misaligned"] >= 1


def test_conn_attach_plain_horizontal_wall_allowed() -> None:
    diagram = """\
┌────┐   ┌────┐
│ A  │──▶│ B  │
└────┘   └────┘
"""
    stats = detect_misaligned(diagram, require_at_least_one_rect=False)
    assert stats["misaligned"] == 0
