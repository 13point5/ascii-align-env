from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# Direction bitmask
N, E, S, W = 1, 2, 4, 8

ALLOWED_BOX_CHARS = {
    "┌",
    "┐",
    "└",
    "┘",
    "─",
    "│",
    "├",
    "┤",
    "┬",
    "┴",
    "┼",
}

BOX_DRAWING_START = 0x2500
BOX_DRAWING_END = 0x257F

ARROW_INCOMING = {
    "▶": W,
    ">": W,
    "◀": E,
    "<": E,
    "▲": S,
    "^": S,
    "▼": N,
    "v": N,
}

UNICODE_ARROWS = {"▶", "◀", "▲", "▼"}
ASCII_ARROWS = {">", "<", "^", "v"}

DIR_STEPS = {
    N: (-1, 0),
    E: (0, 1),
    S: (1, 0),
    W: (0, -1),
}


def _opposite(direction: int) -> int:
    return {N: S, E: W, S: N, W: E}[direction]


def build_dir_map() -> Dict[str, int]:
    """Map allowed box-drawing characters to directional connectivity."""
    return {
        "┌": E | S,
        "┐": W | S,
        "└": E | N,
        "┘": W | N,
        "─": E | W,
        "│": N | S,
        "├": N | E | S,
        "┤": N | W | S,
        "┬": E | W | S,
        "┴": E | W | N,
        "┼": N | E | S | W,
    }


DIR_MAP = build_dir_map()


def strip_ansi(s: str) -> str:
    """Remove ANSI escape codes (colored terminal output)."""
    import re

    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    return ansi.sub("", s)


def find_disallowed_box_drawing_chars(diagram: str) -> set[str]:
    """
    Return any Unicode box-drawing chars not in the allowed structural set.
    Non-box content chars are permitted.
    """
    cleaned = strip_ansi(diagram)
    return {
        ch
        for ch in cleaned
        if BOX_DRAWING_START <= ord(ch) <= BOX_DRAWING_END and ch not in ALLOWED_BOX_CHARS
    }


def has_disallowed_box_drawing_chars(diagram: str) -> bool:
    return len(find_disallowed_box_drawing_chars(diagram)) > 0


def normalize_grid(diagram: str) -> List[List[str]]:
    """
    Convert diagram into a rectangular 2D char grid:
    - strip ANSI
    - expand tabs
    - pad all lines to same width
    """
    diagram = strip_ansi(diagram.expandtabs())
    lines = diagram.splitlines()
    if not lines:
        return []
    width = max(len(line) for line in lines)
    return [list(line.ljust(width)) for line in lines]


def dirs(ch: str) -> int:
    return DIR_MAP.get(ch, 0)


def _in_bounds(grid: List[List[str]], r: int, c: int) -> bool:
    height = len(grid)
    width = len(grid[0]) if height else 0
    return 0 <= r < height and 0 <= c < width


def connected(grid: List[List[str]], r: int, c: int, dr: int, dc: int) -> bool:
    """True if cell (r,c) and (r+dr,c+dc) mutually connect as structural chars."""
    r2, c2 = r + dr, c + dc
    if not _in_bounds(grid, r2, c2):
        return False

    d1, d2 = dirs(grid[r][c]), dirs(grid[r2][c2])

    if dr == 0 and dc == 1:  # east
        return bool((d1 & E) and (d2 & W))
    if dr == 0 and dc == -1:  # west
        return bool((d1 & W) and (d2 & E))
    if dr == 1 and dc == 0:  # south
        return bool((d1 & S) and (d2 & N))
    if dr == -1 and dc == 0:  # north
        return bool((d1 & N) and (d2 & S))

    raise ValueError("Invalid direction step")


def edge_row_ok(grid: List[List[str]], r: int, c0: int, c1: int) -> bool:
    """All consecutive pairs along row r between c0..c1 must be mutually connected."""
    step = 1 if c1 >= c0 else -1
    for c in range(c0, c1, step):
        if not connected(grid, r, c, 0, step):
            return False
    return True


def edge_col_ok(grid: List[List[str]], c: int, r0: int, r1: int) -> bool:
    """All consecutive pairs along column c between r0..r1 must be mutually connected."""
    step = 1 if r1 >= r0 else -1
    for r in range(r0, r1, step):
        if not connected(grid, r, c, step, 0):
            return False
    return True


def is_tl(ch: str) -> bool:
    return ch == "┌"


def is_tr(ch: str) -> bool:
    return ch == "┐"


def is_bl(ch: str) -> bool:
    return ch == "└"


def is_br(ch: str) -> bool:
    return ch == "┘"


def _detect_rectangles(grid: List[List[str]]) -> tuple[int, int]:
    """Return (correct_rectangles, rectangle_errors)."""
    if not grid:
        return (0, 0)

    height = len(grid)
    width = len(grid[0])

    # Find TL candidates: must connect right and down with mutual connectivity.
    tls = []
    for r in range(height):
        for c in range(width):
            if is_tl(grid[r][c]) and connected(grid, r, c, 0, 1) and connected(grid, r, c, 1, 0):
                tls.append((r, c))

    rectangles = 0
    failed_tl = 0

    for r0, c0 in tls:
        closed = False

        for c1 in range(c0 + 1, width):
            if not is_tr(grid[r0][c1]):
                continue
            if not edge_row_ok(grid, r0, c0, c1):
                continue

            for r2 in range(r0 + 1, height):
                if is_bl(grid[r2][c0]) and is_br(grid[r2][c1]):
                    if (
                        edge_col_ok(grid, c0, r0, r2)
                        and edge_col_ok(grid, c1, r0, r2)
                        and edge_row_ok(grid, r2, c0, c1)
                    ):
                        rectangles += 1
                        closed = True
                        break
            if closed:
                break

        if not closed:
            failed_tl += 1

    return (rectangles, failed_tl)


def _is_plain_wall_attachment(direction: int, neighbor_ch: str) -> bool:
    # Relaxed rule: connectors may attach to plain walls.
    if direction in (E, W) and neighbor_ch == "│":
        return True
    if direction in (N, S) and neighbor_ch == "─":
        return True
    return False


def _arrow_accepts_from(arrow_ch: str, direction_from_neighbor: int) -> bool:
    return ARROW_INCOMING.get(arrow_ch) == direction_from_neighbor


def _is_arrow_symbol(grid: List[List[str]], r: int, c: int) -> bool:
    ch = grid[r][c]
    if ch in UNICODE_ARROWS:
        return True
    if ch not in ASCII_ARROWS:
        return False

    # Reject plain word characters immediately.
    for dr, dc in DIR_STEPS.values():
        r2, c2 = r + dr, c + dc
        if _in_bounds(grid, r2, c2) and grid[r2][c2].isalnum():
            return False

    # Avoid treating letters in words as arrows (e.g. 'Service').
    expected = ARROW_INCOMING[ch]
    dr, dc = DIR_STEPS[expected]
    r2, c2 = r + dr, c + dc
    return _in_bounds(grid, r2, c2) and grid[r2][c2] in DIR_MAP


def _has_label_bridge_horizontal(grid: List[List[str]], r: int, c: int, direction: int) -> bool:
    """
    Supports: ── label ──▶
    Rule: there must be label text in the gap and a resumed line segment after the text.
    """
    if direction not in (E, W):
        return False
    if not (dirs(grid[r][c]) & direction):
        return False

    step = 1 if direction == E else -1
    width = len(grid[0]) if grid else 0

    i = c + step
    saw_label_char = False

    while 0 <= i < width:
        ch = grid[r][i]
        if ch in DIR_MAP or ch in ARROW_INCOMING:
            break
        if ch != " ":
            saw_label_char = True
        i += step

    if not (0 <= i < width):
        return False
    if not saw_label_char:
        return False

    target = grid[r][i]
    opposite = _opposite(direction)

    # No resumed segment before arrowhead => invalid bridge.
    if target in ARROW_INCOMING:
        return False

    has_opposite_port = bool(dirs(target) & opposite)
    is_plain_attachment = _is_plain_wall_attachment(direction, target)
    if not (has_opposite_port or is_plain_attachment):
        return False

    # Plain-wall endpoint requires a resumed segment right next to the wall.
    if is_plain_attachment and not has_opposite_port:
        inward_step = -step
        k = i + inward_step
        if not (0 <= k < width):
            return False
        inner = grid[r][k]
        if inner not in DIR_MAP:
            return False
        if not (
            (dirs(inner) & direction)
            or (dirs(inner) & opposite)
            or _is_plain_wall_attachment(direction, inner)
        ):
            return False
        return True

    # Endpoint target (e.g., ┤) is acceptable if it receives from the bridge side.
    if not (dirs(target) & direction):
        return True

    j = i + step
    if not (0 <= j < width):
        return False

    next_ch = grid[r][j]
    if next_ch in DIR_MAP and (
        connected(grid, r, i, 0, step) or _is_plain_wall_attachment(direction, next_ch)
    ):
        return True
    if next_ch in ARROW_INCOMING and _arrow_accepts_from(next_ch, opposite):
        return True

    return False


def _has_label_bridge_vertical(grid: List[List[str]], r: int, c: int, direction: int) -> bool:
    """
    Permissive vertical bridge for labeled connectors, e.g.:
      ┴
      Pass
       │

    Supports a one-column drift at the target after label text.
    """
    if direction not in (N, S):
        return False
    if not (dirs(grid[r][c]) & direction):
        return False

    step = -1 if direction == N else 1
    height = len(grid)

    i = r + step
    saw_label_char = False

    while 0 <= i < height:
        ch = grid[i][c]
        if ch in DIR_MAP or ch in ARROW_INCOMING:
            break
        if ch != " ":
            saw_label_char = True
        i += step

    if not (0 <= i < height):
        return False
    if not saw_label_char:
        return False

    opposite = _opposite(direction)
    candidates = [c]
    if c - 1 >= 0:
        candidates.append(c - 1)
    if c + 1 < len(grid[0]):
        candidates.append(c + 1)

    for c2 in candidates:
        target = grid[i][c2]
        if target in DIR_MAP and ((dirs(target) & opposite) or _is_plain_wall_attachment(direction, target)):
            return True
    return False


def _port_satisfied(grid: List[List[str]], r: int, c: int, direction: int) -> bool:
    dr, dc = DIR_STEPS[direction]
    r2, c2 = r + dr, c + dc
    if not _in_bounds(grid, r2, c2):
        return False

    source_ch = grid[r][c]
    neighbor_ch = grid[r2][c2]

    if neighbor_ch in DIR_MAP:
        if connected(grid, r, c, dr, dc):
            return True
        if _is_plain_wall_attachment(direction, neighbor_ch):
            return True

    if _is_arrow_symbol(grid, r2, c2) and _arrow_accepts_from(neighbor_ch, _opposite(direction)):
        return True

    if direction in (E, W) and _has_label_bridge_horizontal(grid, r, c, direction):
        return True
    if direction in (N, S) and _has_label_bridge_vertical(grid, r, c, direction):
        return True

    _ = source_ch
    return False


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[tuple[int, int], tuple[int, int]] = {}

    def add(self, x: tuple[int, int]) -> None:
        if x not in self.parent:
            self.parent[x] = x

    def find(self, x: tuple[int, int]) -> tuple[int, int]:
        p = self.parent[x]
        if p != x:
            self.parent[x] = self.find(p)
        return self.parent[x]

    def union(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _collect_connector_positions(grid: List[List[str]]) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in DIR_MAP:
                positions.append((r, c))
    return positions


def _pair_gap_event(
    grid: List[List[str]],
    unresolved_set: set[tuple[int, int, int]],
    r: int,
    c: int,
    direction: int,
) -> tuple[str, int, int, int] | None:
    dr, dc = DIR_STEPS[direction]
    r2, c2 = r + dr, c + dc

    while _in_bounds(grid, r2, c2):
        ch = grid[r2][c2]
        if ch in ARROW_INCOMING:
            return None
        if ch in DIR_MAP:
            opposite = _opposite(direction)
            if (r2, c2, opposite) in unresolved_set:
                if direction in (E, W):
                    return ("h", r, min(c, c2), max(c, c2))
                return ("v", c, min(r, r2), max(r, r2))
            return None
        r2 += dr
        c2 += dc

    return None


def _count_connector_errors(grid: List[List[str]]) -> int:
    positions = _collect_connector_positions(grid)
    if not positions:
        return 0

    uf = _UnionFind()
    for pos in positions:
        uf.add(pos)

    # Build semantic connectivity components (mutual only). This keeps
    # connector-only runs separate from surrounding box components.
    for r, c in positions:
        dmask = dirs(grid[r][c])
        for direction in (N, E, S, W):
            if not (dmask & direction):
                continue
            dr, dc = DIR_STEPS[direction]
            r2, c2 = r + dr, c + dc
            if not _in_bounds(grid, r2, c2):
                continue
            ch2 = grid[r2][c2]
            if ch2 not in DIR_MAP:
                continue
            if connected(grid, r, c, dr, dc):
                uf.union((r, c), (r2, c2))

    unresolved: list[tuple[int, int, int]] = []
    for r, c in positions:
        dmask = dirs(grid[r][c])
        for direction in (N, E, S, W):
            if dmask & direction and not _port_satisfied(grid, r, c, direction):
                unresolved.append((r, c, direction))

    if not unresolved:
        return _count_arrow_only_connector_runs(grid)

    unresolved_set = set(unresolved)
    paired_ports: set[tuple[int, int, int]] = set()
    paired_events: list[tuple[tuple[int, int], tuple[int, int], tuple[str, int, int, int]]] = []

    for r, c, direction in unresolved:
        if (r, c, direction) in paired_ports:
            continue
        event = _pair_gap_event(grid, unresolved_set, r, c, direction)
        if event is None:
            continue

        dr, dc = DIR_STEPS[direction]
        r2, c2 = r + dr, c + dc
        while _in_bounds(grid, r2, c2):
            if grid[r2][c2] in DIR_MAP:
                opposite = _opposite(direction)
                if (r2, c2, opposite) in unresolved_set:
                    paired_ports.add((r, c, direction))
                    paired_ports.add((r2, c2, opposite))
                    paired_events.append(((r, c), (r2, c2), event))
                break
            r2 += dr
            c2 += dc

        # Collapse opposite unresolved ends of the same gap into one component.
        uf.union((r, c), (r2, c2))

    # Count one error per semantic connector component with any unresolved ports,
    # excluding box-like malformed components (accounted by rectangle_errors).
    bad_components: set[tuple[int, int]] = set()
    component_chars: dict[tuple[int, int], set[str]] = {}
    for r, c in positions:
        root = uf.find((r, c))
        component_chars.setdefault(root, set()).add(grid[r][c])

    def is_box_like(root: tuple[int, int]) -> bool:
        chars = component_chars.get(root, set())
        return chars.issubset({"┌", "┐", "└", "┘", "─", "│"}) and any(
            ch in {"┌", "┐", "└", "┘"} for ch in chars
        )

    for r, c, direction in unresolved:
        if (r, c, direction) in paired_ports:
            continue
        root = uf.find((r, c))
        if not is_box_like(root):
            bad_components.add(root)

    # Merge nearby bad components into one connector event.
    bad_roots = list(bad_components)
    if not bad_roots:
        bad_clusters = 0
    else:
        comp_cells: dict[tuple[int, int], list[tuple[int, int]]] = {root: [] for root in bad_roots}
        for r, c in positions:
            root = uf.find((r, c))
            if root in comp_cells:
                comp_cells[root].append((r, c))

        seen: set[tuple[int, int]] = set()
        bad_clusters = 0
        for root in bad_roots:
            if root in seen:
                continue
            bad_clusters += 1
            stack = [root]
            seen.add(root)
            while stack:
                cur = stack.pop()
                for other in bad_roots:
                    if other in seen or other == cur:
                        continue
                    close = False
                    for r1, c1 in comp_cells[cur]:
                        for r2, c2 in comp_cells[other]:
                            if abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                                close = True
                                break
                        if close:
                            break
                    if close:
                        seen.add(other)
                        stack.append(other)

    gap_events: set[tuple[str, int, int, int]] = set()
    for (r1, c1), (r2, c2), event in paired_events:
        root = uf.find((r1, c1))
        if uf.find((r2, c2)) != root:
            continue
        if is_box_like(root):
            continue
        gap_events.add(event)

    return bad_clusters + len(gap_events) + _count_arrow_only_connector_runs(grid)


def _count_arrow_only_connector_runs(grid: List[List[str]]) -> int:
    """
    Count connector runs that only bridge between arrowheads and never attach
    to a non-arrow structural anchor (box/junction). These are usually
    free-floating arrow-to-arrow lines.
    """
    positions = _collect_connector_positions(grid)
    if not positions:
        return 0

    uf = _UnionFind()
    for pos in positions:
        uf.add(pos)

    for r, c in positions:
        dmask = dirs(grid[r][c])
        for direction in (N, E, S, W):
            if not (dmask & direction):
                continue
            dr, dc = DIR_STEPS[direction]
            r2, c2 = r + dr, c + dc
            if _in_bounds(grid, r2, c2) and grid[r2][c2] in DIR_MAP and connected(grid, r, c, dr, dc):
                uf.union((r, c), (r2, c2))

    roots: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r, c in positions:
        roots.setdefault(uf.find((r, c)), []).append((r, c))

    errors = 0
    for cells in roots.values():
        chars = {grid[r][c] for r, c in cells}
        if not chars.issubset({"│", "─"}):
            continue

        arrow_neighbors: set[str] = set()
        has_structural_anchor = False
        for r, c in cells:
            dmask = dirs(grid[r][c])
            for direction in (N, E, S, W):
                if not (dmask & direction):
                    continue
                dr, dc = DIR_STEPS[direction]
                r2, c2 = r + dr, c + dc
                if not _in_bounds(grid, r2, c2):
                    continue
                nbr = grid[r2][c2]
                if nbr in DIR_MAP and not connected(grid, r, c, dr, dc):
                    if _is_plain_wall_attachment(direction, nbr):
                        has_structural_anchor = True
                if _is_arrow_symbol(grid, r2, c2):
                    arrow_neighbors.add(nbr)

        if has_structural_anchor:
            continue
        if {"▲", "▼"} <= arrow_neighbors or {"^", "v"} <= arrow_neighbors:
            errors += 1
        elif {"◀", "▶"} <= arrow_neighbors or {"<", ">"} <= arrow_neighbors:
            errors += 1

    return errors


def _count_arrow_errors(grid: List[List[str]]) -> int:
    arrow_errors = 0

    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if not _is_arrow_symbol(grid, r, c):
                continue

            expected = ARROW_INCOMING[ch]
            incoming_found: set[int] = set()

            for direction in (N, E, S, W):
                dr, dc = DIR_STEPS[direction]
                r2, c2 = r + dr, c + dc
                if not _in_bounds(grid, r2, c2):
                    continue
                neighbor = grid[r2][c2]
                if neighbor in DIR_MAP and (dirs(neighbor) & _opposite(direction)):
                    incoming_found.add(direction)

            if incoming_found != {expected}:
                arrow_errors += 1
                continue

            # Up arrows should point at a visible target above, not empty space.
            if ch in {"▲", "^"}:
                out_dir = _opposite(expected)
                dr, dc = DIR_STEPS[out_dir]
                r2, c2 = r + dr, c + dc
                if _in_bounds(grid, r2, c2) and grid[r2][c2] == " ":
                    arrow_errors += 1

    return arrow_errors


def detect_misaligned(diagram: str, require_at_least_one_rect: bool = True) -> Dict[str, int]:
    """
    Returns diagnostics:
    - correct_rectangles: number of closed rectangles
    - rectangle_errors: failed rectangle closures
    - connector_errors: broken/dangling connector runs
    - arrow_errors: invalid arrowheads (wrong/missing incoming shaft)
    - misaligned: total error count

    Backward compatibility:
    - correct is retained as an alias for correct_rectangles.
    """
    grid = normalize_grid(diagram)

    correct_rectangles, rectangle_errors = _detect_rectangles(grid)
    connector_errors = _count_connector_errors(grid)
    arrow_errors = _count_arrow_errors(grid)

    if require_at_least_one_rect and correct_rectangles == 0:
        rectangle_errors = max(1, rectangle_errors)

    misaligned = rectangle_errors + connector_errors + arrow_errors

    return {
        "correct_rectangles": correct_rectangles,
        "rectangle_errors": rectangle_errors,
        "connector_errors": connector_errors,
        "arrow_errors": arrow_errors,
        "correct": correct_rectangles,
        "misaligned": misaligned,
    }
