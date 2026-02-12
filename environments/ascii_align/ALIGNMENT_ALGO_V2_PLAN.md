# ASCII Alignment Checker v2 Plan

## Goal
Replace the current heuristic checker with a shape-aware detector that catches the false positives in `environments/ascii_align/tests/false-positives/01.md`, `environments/ascii_align/tests/false-positives/02.md`, and `environments/ascii_align/tests/false-positives/03.md`, with emphasis on:

- misaligned box borders (row-to-row edge drift inside a box)
- missing/broken connector lines
- dangling arrows with no valid start and/or end anchor

## Current Behavior Review (why false positives pass)

Current implementation (`environments/ascii_align/alignment_check.py`) misses important malformed structures:

Baseline check today: all three false-positive fixtures currently return `misaligned=0`.

1. `_detect_rectangles` only counts failures from top-left (`┌`) starters and closed-rectangle attempts (lines 176-219).
- If a malformed box row shifts right (` │ ... │` / ` └...┘`) and no valid `┌` start is available for that malformed shape, it may never produce `rectangle_errors`.

2. `_count_connector_errors` intentionally suppresses unresolved ports for `is_box_like` components (lines 526-545).
- This hides malformed box fragments when rectangle logic did not catch them.

3. `_count_arrow_errors` validates incoming shaft direction but only enforces outgoing target visibility for up arrows (`▲`, `^`) (lines 681-688).
- Patterns like dangling down arrows or orphan fragments such as `◄───┘` can pass.

4. There is no residual-structure pass.
- After counting rectangles/connectors/arrows, leftover structural glyph clusters are not explicitly treated as malformed artifacts.

## v2 Algorithm Design

### 1) Parse to typed structural grid
Create a `CellKind` classification for each char:
- `corner`: `┌┐└┘`
- `line`: `─│`
- `junction`: `├┤┬┴┼`
- `arrow`: `▶◀▲▼><^v`
- `text/space`

Reuse `normalize_grid` and direction masks, but keep a per-cell metadata table with:
- directional ports
- component id
- whether consumed by a validated primitive

### 2) Detect box candidates by span, then validate edge consistency
For each row, detect horizontal top/bottom spans:
- top span: `┌─...─┐`
- bottom span: `└─...─┘`

Pair candidate tops/bottoms by matching `(left_col, right_col)` and `top_row < bottom_row`.

For each paired candidate:
- every interior row must contain `│` at exactly `left_col` and `right_col`
- no interior row may move either wall (`left_col +/- 1`, `right_col +/- 1` is invalid)
- optional interior junction chars are allowed only if ports remain consistent with neighbors

Outputs:
- `valid_boxes`
- `malformed_box_events` (one per invalid box candidate cluster)
- mark all cells used by valid boxes as `consumed`

This directly targets the reported edge-drift failures (including the problematic rows around "Send Notification" / "Notification Service" when those box rows drift).

### 3) Build connector graph from unconsumed structural cells
On non-consumed line/junction cells:
- build adjacency only through mutual compatible ports
- compute connected components

For each component, enforce:
- all open ports must terminate at a valid anchor:
  - box wall attachment (allowed anywhere on wall, per your preference)
  - junction continuation
  - arrow incoming side
- gap pairing is allowed only when both sides belong to one logical broken span event

Any component with unresolved ports after pairing => `connector_error` event.

### 4) Strict arrow object validation (all directions)
For each arrow cell:
- incoming side must have exactly one valid shaft neighbor
- outgoing side must point to a valid immediate target context:
  - box wall, connector/junction, or a non-space structural continuation
- reject arrows whose shaft side ends in orphan corner fragments (`◄───┘` with no valid source component)

This is symmetric for `▶◀▲▼><^v` (not only up arrows).

### 5) Residual structural artifact pass
After valid boxes + connector components + valid arrows are marked, scan remaining structural chars (`┌┐└┘─│├┤┬┴┼`):
- cluster by 8-neighborhood
- each leftover cluster counts as one `artifact_error`

Map `artifact_error` to:
- `rectangle_errors` when cluster is corner-heavy / box-shaped
- `connector_errors` otherwise

This closes the largest false-positive hole: malformed fragments that were ignored by both rectangle and connector counters.

### 6) Scoring compatibility
Preserve output schema:
- `correct_rectangles`
- `rectangle_errors`
- `connector_errors`
- `arrow_errors`
- `misaligned`
- alias `correct`

No reward API change in `environments/ascii_align/ascii_align.py`; `alignment_reward` continues using `correct / (correct + misaligned)`.

## Test Plan

### A. Wire existing markdown fixtures into pytest
Add a new test module:
- `environments/ascii_align/tests/test_alignment_false_positives_md.py`

Behavior:
- load each file in `environments/ascii_align/tests/false-positives/*.md`
- extract the ` ```text ... ``` ` block
- assert exact diagnostic counts for each fixture (lock regression behavior)
- include named sub-assertions for the `Send Notification` and `Notification Service` sections so box-edge drift is explicitly covered

### B. Add new regression fixtures for currently missed patterns
Add cases (inline or fixture files):

1. `orphan_arrow_corner`
```text
┌───────────┐
│  Node     │◄───┘
└───────────┘
```

2. `dangling_down_arrow_no_target`
```text
┌───────────┐
│  Node     │
└───────────┘
     │
     ▼
```

3. `mixed_valid_and_shifted_box`
```text
┌───────────┐
│  Good     │
└───────────┘

┌───────────┐
 │  Bad A    │
 │  Bad B    │
 └───────────┘
```

4. `multi_box_edge_drift_cluster` (multiple shifted rows inside one malformed box)

Each of these is currently a false positive (`misaligned=0`) and should become failing after v2.

### C. Keep and verify non-regression controls
Retain existing passing tests for:
- clean rectangles
- valid connectors
- valid label bridges
- valid arrow directions

Add explicit controls for "arrow can attach anywhere on box wall" so the new algorithm does not regress your preferred permissive anchor-position rule.

## Implementation Steps (ordered)

1. Add a new internal checker module:
- `environments/ascii_align/alignment_check_v2.py`

2. Implement box span extraction + box validation + consumed-cell tracking.

3. Implement connector component validation over unconsumed cells.

4. Implement symmetric arrow validation and orphan-tail detection.

5. Implement residual artifact clustering and error routing.

6. Build a parity adapter in `detect_misaligned`:
- temporary flag to compare old vs v2 outputs during rollout (`use_v2=True` default in tests, optional fallback during migration).

7. Add new false-positive markdown loader tests and expanded regressions.

8. Remove old-path fallback once parity + regressions are stable.

## Acceptance Criteria

- All three markdown false-positive fixtures fail (`misaligned > 0`) with exact expected diagnostics locked in tests.
- New orphan/dangling/edge-drift cases fail with exact expected diagnostics.
- Existing valid-shape tests continue passing.
- Runtime remains within current test budget (no significant slowdown on current fixture sizes).

## Assumptions

- Connector/arrow attachment to box walls remains permissive by position (any wall point is allowed).
- The objective is structural validity, not text centering quality.
- Exact per-fixture expected counts will be finalized immediately after first v2 implementation run and then frozen in tests.
