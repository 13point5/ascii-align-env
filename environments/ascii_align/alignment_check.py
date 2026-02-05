from typing import List, Dict

# Direction bitmask
N, E, S, W = 1, 2, 4, 8


def build_dir_map():
    """
    Map box-drawing characters to which directions they connect.
    Extend this if your model uses additional characters.
    """
    m = {}

    # Single-line box drawing
    m.update(
        {
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
            # Rounded corners
            "╭": E | S,
            "╮": W | S,
            "╰": E | N,
            "╯": W | N,
        }
    )

    # Double-line box drawing
    m.update(
        {
            "╔": E | S,
            "╗": W | S,
            "╚": E | N,
            "╝": W | N,
            "═": E | W,
            "║": N | S,
            "╠": N | E | S,
            "╣": N | W | S,
            "╦": E | W | S,
            "╩": E | W | N,
            "╬": N | E | S | W,
        }
    )

    # ASCII fallback
    m.update(
        {
            "+": N | E | S | W,  # treat as full junction (corner/intersection)
            "-": E | W,
            "=": E | W,
            "|": N | S,
        }
    )

    return m


DIR_MAP = build_dir_map()


def strip_ansi(s: str) -> str:
    """Remove ANSI escape codes (colored terminal output)."""
    import re

    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    return ansi.sub("", s)


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
    w = max(len(l) for l in lines)
    return [list(l.ljust(w)) for l in lines]


def dirs(ch: str) -> int:
    return DIR_MAP.get(ch, 0)


def connected(grid: List[List[str]], r: int, c: int, dr: int, dc: int) -> bool:
    """
    True if cell (r,c) and its neighbor (r+dr,c+dc) mutually connect.
    """
    H = len(grid)
    Wd = len(grid[0]) if H else 0
    r2, c2 = r + dr, c + dc
    if not (0 <= r2 < H and 0 <= c2 < Wd):
        return False

    d1, d2 = dirs(grid[r][c]), dirs(grid[r2][c2])

    if dr == 0 and dc == 1:  # east
        return (d1 & E) and (d2 & W)
    if dr == 0 and dc == -1:  # west
        return (d1 & W) and (d2 & E)
    if dr == 1 and dc == 0:  # south
        return (d1 & S) and (d2 & N)
    if dr == -1 and dc == 0:  # north
        return (d1 & N) and (d2 & S)

    raise ValueError("Invalid direction step")


def edge_row_ok(grid, r, c0, c1) -> bool:
    """All consecutive pairs along row r between c0..c1 must be connected."""
    step = 1 if c1 >= c0 else -1
    for c in range(c0, c1, step):
        if not connected(grid, r, c, 0, step):
            return False
    return True


def edge_col_ok(grid, c, r0, r1) -> bool:
    """All consecutive pairs along col c between r0..r1 must be connected."""
    step = 1 if r1 >= r0 else -1
    for r in range(r0, r1, step):
        if not connected(grid, r, c, step, 0):
            return False
    return True


def is_tl(ch):  # top-left-like
    d = dirs(ch)
    return (d & E) and (d & S)


def is_tr(ch):  # top-right-like
    d = dirs(ch)
    return (d & W) and (d & S)


def is_bl(ch):  # bottom-left-like
    d = dirs(ch)
    return (d & E) and (d & N)


def is_br(ch):  # bottom-right-like
    d = dirs(ch)
    return (d & W) and (d & N)


def detect_misaligned(diagram: str, require_at_least_one_rect: bool = True) -> Dict[str, int]:
    """
    Returns diagnostics: dict with readable keys.
    - correct: number of closed rectangles
    - misaligned: number of TL corners that couldn't close (min 1 if required and no rectangles)
    """
    grid = normalize_grid(diagram)
    if not grid:
        return {
            "correct": 0,
            "misaligned": 1 if require_at_least_one_rect else 0,
        }

    H = len(grid)
    Wd = len(grid[0])

    # Find TL candidates: must connect right and down (with actual neighbor connectivity)
    TLs = []
    for r in range(H):
        for c in range(Wd):
            if is_tl(grid[r][c]) and connected(grid, r, c, 0, 1) and connected(grid, r, c, 1, 0):
                TLs.append((r, c))

    rectangles = []
    failed_tl = 0

    # Attempt to close a rectangle from each TL
    for r0, c0 in TLs:
        closed = False

        # Look for a TR on same row that forms a valid top edge
        for c1 in range(c0 + 1, Wd):
            if not is_tr(grid[r0][c1]):
                continue
            if not edge_row_ok(grid, r0, c0, c1):
                continue

            # Look for matching bottom corners and valid left/right/bottom edges
            for r2 in range(r0 + 1, H):
                if is_bl(grid[r2][c0]) and is_br(grid[r2][c1]):
                    if (
                        edge_col_ok(grid, c0, r0, r2)
                        and edge_col_ok(grid, c1, r0, r2)
                        and edge_row_ok(grid, r2, c0, c1)
                    ):
                        rectangles.append((r0, c0, r2, c1))
                        closed = True
                        break
            if closed:
                break

        if not closed:
            failed_tl += 1
            # Keep scanning so we can count all closed rectangles for diagnostics.

    misaligned = failed_tl
    if require_at_least_one_rect and len(rectangles) == 0:
        misaligned = max(1, misaligned)

    return {"correct": len(rectangles), "misaligned": misaligned}


# -------------------------
# Test cases
# -------------------------
def _run_tests():
    test_cases = [
        {
            "name": "ok_basic_box",
            "diagram": """\
┌───────────┐
│   hello   │
│   world   │
└───────────┘
""",
            "misaligned": False,
        },
        {
            "name": "ok_nested_box",
            "diagram": """\
┌──────────────┐
│ ┌──────┐     │
│ │ A    │     │
│ └──────┘     │
└──────────────┘
""",
            "misaligned": False,
        },
        {
            "name": "ok_ascii_box",
            "diagram": """\
+--------+
| hello  |
+--------+
""",
            "misaligned": False,
        },
        {
            "name": "ok_multi_boxes",
            "diagram": """\
┌─────────────────────────┐
│ ┌──────┐  ┌───────────┐ │
│ │ Box1 │  │   Box2    │ │
│ └──────┘  └───────────┘ │
│        ┌──────┐         │
│        │Box3  │         │
│        └──────┘         │
└─────────────────────────┘
""",
            "misaligned": False,
        },
        {
            "name": "bad_ascii_width_mismatch",
            "diagram": """\
+--------+
| hello  |
+---------+
""",
            "misaligned": True,
        },
        {
            "name": "bad_nested_shifted_corner",
            "diagram": """\
┌──────────────┐
│ ┌──────┐     │
│ │ A    │     │
│  └──────┘    │
└──────────────┘
""",
            "misaligned": True,
        },
        {
            "name": "bad_bottom_right_inset",
            "diagram": """\
┌───────────┐
│   hello   │
│   world  │
└──────────┘
""",
            "misaligned": True,
        },
        {
            "name": "bad_multi_outer_right_shift",
            "diagram": """\
┌─────────────────────────┐
│ ┌──────┐  ┌───────────┐ │
│ │ Box1 │  │   Box2    │ │
│ └──────┘  │   mid     │  │
│           └───────────┘ │
│        ┌──────┐         │
│        │Box3  │         │
│        └──────┘         │
└─────────────────────────┘
""",
            "misaligned": True,
        },
    ]

    for case in test_cases:
        info = detect_misaligned(case["diagram"])
        print(case["name"], "info=", info)
        is_misaligned = info["misaligned"] > 0
        assert is_misaligned == case["misaligned"], (
            f"{case['name']}: expected {case['misaligned']} got {is_misaligned} info={info}"
        )
        for key, value in case.get("info", {}).items():
            assert info.get(key) == value, (
                f"{case['name']}: expected info[{key}]={value} got {info.get(key)}"
            )

    print("ALL TESTS PASSED ✅")


if __name__ == "__main__":
    _run_tests()
