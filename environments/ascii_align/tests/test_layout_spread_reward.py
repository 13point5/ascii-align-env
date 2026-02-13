import sys
import types


if "verifiers" not in sys.modules:
    sys.modules["verifiers"] = types.SimpleNamespace(Environment=object, Rubric=object, SingleTurnEnv=object)
if "datasets" not in sys.modules:
    sys.modules["datasets"] = types.SimpleNamespace(load_dataset=lambda *args, **kwargs: None)

from ascii_align import layout_spread_reward


def _completion(content: str) -> list[dict[str, str]]:
    return [{"role": "assistant", "content": content}]


def test_layout_spread_rollout_sequence_vertical_stack_is_low() -> None:
    # Inspired by rollout qckmeg2wm4dsyn9npvwzczs2 (step 290, sequence sample).
    response = """```text
┌────────────┐
│   Client   │
└────────────┘
      ↓
┌────────────┐
│ Edge Cache │
└────────────┘
      ↓
┌────────────┐
│ Vector DB  │
└────────────┘
      ↓
┌────────────┐
│ Monitoring │
└────────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "sequence", "shape_budget": 8},
    )
    assert score == 0.0


def test_layout_spread_rollout_flowchart_vertical_stack_is_low() -> None:
    # Inspired by rollout b24wfgo7jwdq5pl1cc342nwa (step 290, flowchart sample).
    response = """```text
┌──────────────────┐
│ Receive Request  │
└──────────────────┘
         ↓
┌──────────────────┐
│ Validate Auth    │
└──────────────────┘
         ↓
┌──────────────────┐
│ Security Check   │
└──────────────────┘
         ↓
┌──────────────────┐
│ Send Event Queue │
└──────────────────┘
         ↓
┌──────────────────┐
│ Process Recovery │
└──────────────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "flowcharts", "shape_budget": 8},
    )
    assert score == 0.0


def test_layout_spread_sequence_horizontal_layout_scores_high() -> None:
    # Based on sequence-style prompts present in the dataset.
    response = """```text
┌────────┐   ┌────────┐   ┌────────┐   ┌────────────┐
│ Client │──▶│ API    │──▶│ AuthDB │──▶│ Session    │
└────────┘   └────────┘   └────────┘   └────────────┘
   ▲                                           │
   └──────────────────────────◀────────────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "sequence", "shape_budget": 8},
    )
    assert score >= 0.9


def test_layout_spread_architecture_with_side_branch_scores_high() -> None:
    # Based on architecture prompts in the dataset (API, queue, workers, metrics).
    response = """```text
      ┌──────────┐
      │   API    │
      └──────────┘
           │
   ┌───────┼───────┐
   ▼               ▼
┌──────────┐   ┌──────────┐
│ Queue    │   │ Metrics  │
└──────────┘   └──────────┘
      │
      ▼
┌──────────┐
│ Worker   │
└──────────┘
      │
      ▼
┌──────────┐
│ Postgres │
└──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "architecture", "shape_budget": 8},
    )
    assert score >= 0.55


def test_layout_spread_high_budget_two_column_grid_is_partial() -> None:
    # High shape budgets should not fully reward only two columns.
    response = """```text
┌────┐   ┌────┐
│ A  │   │ B  │
└────┘   └────┘
  │        │
┌────┐   ┌────┐
│ C  │   │ D  │
└────┘   └────┘
  │        │
┌────┐   ┌────┐
│ E  │   │ F  │
└────┘   └────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "flowcharts", "shape_budget": 12},
    )
    assert 0.4 <= score <= 0.65


def test_layout_spread_complex_sequence_with_multiple_participants_scores_high() -> None:
    # More complex sequence-style prompt behavior with multiple participants.
    response = """```text
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Client   │   │ API GW   │   │ AuthSvc  │   │ Session  │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │
     ├─────────────▶│              │              │
     │              ├─────────────▶│              │
     │              │              ├─────────────▶│
     │              │              │              │
     │              │              ◀──────────────┤
     │              ◀──────────────┤              │
     ◀──────────────┤              │              │
     │
┌──────────┐
│ Monitor  │
└──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "sequence", "shape_budget": 12},
    )
    assert score >= 0.9


def test_layout_spread_complex_sequence_vertical_stack_is_low() -> None:
    # A sequence prompt rendered as a single top-to-bottom stack should be penalized.
    response = """```text
┌──────────────┐
│    Client    │
└──────────────┘
       ↓
┌──────────────┐
│   API GW     │
└──────────────┘
       ↓
┌──────────────┐
│   AuthSvc    │
└──────────────┘
       ↓
┌──────────────┐
│  Session DB  │
└──────────────┘
       ↓
┌──────────────┐
│ Retry Logic  │
└──────────────┘
       ↓
┌──────────────┐
│ Alert System │
└──────────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "sequence", "shape_budget": 16},
    )
    assert score == 0.0


def test_layout_spread_complex_state_machine_branching_scores_high() -> None:
    # Complex state machine with multiple branches should get strong spread credit.
    response = """```text
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Queued   │──▶│ Running  │──▶│ Success  │
└────┬─────┘   └────┬─────┘   └──────────┘
     │              │
     │              ├──────────────▶┌──────────┐
     │              │               │ TimedOut │
     │              │               └────┬─────┘
     │              ▼                    │
┌──────────┐   ┌──────────┐              │
│ Canceled │◀──│ Retrying │◀─────────────┘
└──────────┘   └────┬─────┘
                    │
                    ▼
               ┌──────────┐
               │ Failed   │
               └──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "state_machines", "shape_budget": 16},
    )
    assert score >= 0.9


def test_layout_spread_complex_state_machine_vertical_stack_is_low() -> None:
    # High-budget state machine collapsed into one vertical column should score poorly.
    response = """```text
┌────────────┐
│   Queued   │
└────────────┘
      ↓
┌────────────┐
│  Running   │
└────────────┘
      ↓
┌────────────┐
│  Retrying  │
└────────────┘
      ↓
┌────────────┐
│  Running   │
└────────────┘
      ↓
┌────────────┐
│  TimedOut  │
└────────────┘
      ↓
┌────────────┐
│   Failed   │
└────────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "state_machines", "shape_budget": 20},
    )
    assert score == 0.0


def test_layout_spread_complex_state_machine_two_columns_is_partial() -> None:
    # With high shape budget, a two-column state machine should be better than a stack but not full score.
    response = """```text
┌──────────┐       ┌──────────┐
│ Queued   │──▶──▶ │ Running  │
└────┬─────┘       └────┬─────┘
     │                  │
     ▼                  ▼
┌──────────┐       ┌──────────┐
│ Canceled │       │ Retrying │
└──────────┘       └────┬─────┘
                         │
                         ▼
                    ┌──────────┐
                    │ Failed   │
                    └──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "state_machines", "shape_budget": 20},
    )
    assert 0.5 <= score <= 0.75


def test_layout_spread_three_column_dense_flow_is_partial_not_high() -> None:
    # Good column spread, but too many vertically stacked rows per column.
    response = """```text
┌──────┐   ┌──────┐   ┌──────┐
│ A1   │──▶│ B1   │──▶│ C1   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A2   │──▶│ B2   │──▶│ C2   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A3   │──▶│ B3   │──▶│ C3   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A4   │──▶│ B4   │──▶│ C4   │
└──────┘   └──────┘   └──────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "flowcharts", "shape_budget": 20},
    )
    assert 0.45 <= score <= 0.65


def test_layout_spread_three_column_sparse_flow_remains_high() -> None:
    # Similar three-column spread with lower per-column stack depth should stay high.
    response = """```text
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Intake   │──▶│ Validate │──▶│ Commit   │
└──────────┘   └──────────┘   └──────────┘
     │                               │
     ▼                               ▼
┌──────────┐                   ┌──────────┐
│ Retry    │──────────────────▶│ Notify   │
└──────────┘                   └──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "flowcharts", "shape_budget": 20},
    )
    assert score >= 0.9


def test_layout_spread_density_penalty_prefers_sparse_over_dense() -> None:
    dense = """```text
┌──────┐   ┌──────┐   ┌──────┐
│ A1   │──▶│ B1   │──▶│ C1   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A2   │──▶│ B2   │──▶│ C2   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A3   │──▶│ B3   │──▶│ C3   │
└──────┘   └──────┘   └──────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ A4   │──▶│ B4   │──▶│ C4   │
└──────┘   └──────┘   └──────┘
```"""

    sparse = """```text
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Intake   │──▶│ Validate │──▶│ Commit   │
└──────────┘   └──────────┘   └──────────┘
     │                               │
     ▼                               ▼
┌──────────┐                   ┌──────────┐
│ Retry    │──────────────────▶│ Notify   │
└──────────┘                   └──────────┘
```"""

    dense_score = layout_spread_reward(
        _completion(dense),
        info={"theme": "flowcharts", "shape_budget": 20},
    )
    sparse_score = layout_spread_reward(
        _completion(sparse),
        info={"theme": "flowcharts", "shape_budget": 20},
    )
    assert sparse_score > dense_score + 0.25


def test_layout_spread_three_column_dense_state_machine_is_partial() -> None:
    # State machines can be denser than sequence, but deep stacks should still be limited.
    response = """```text
┌────────┐   ┌────────┐   ┌────────┐
│ Q1     │   │ R1     │   │ F1     │
└────────┘   └────────┘   └────────┘
    │           │           │
    ▼           ▼           ▼
┌────────┐   ┌────────┐   ┌────────┐
│ Q2     │   │ R2     │   │ F2     │
└────────┘   └────────┘   └────────┘
    │           │           │
    ▼           ▼           ▼
┌────────┐   ┌────────┐   ┌────────┐
│ Q3     │   │ R3     │   │ F3     │
└────────┘   └────────┘   └────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "state_machines", "shape_budget": 20},
    )
    assert 0.55 <= score <= 0.75


def test_layout_spread_two_column_dense_sequence_is_low() -> None:
    # Sequence diagrams with dense per-column stacks should be heavily penalized.
    response = """```text
┌──────────┐      ┌──────────┐
│ Client1  │────▶ │ API1     │
└──────────┘      └──────────┘
     │                 │
     ▼                 ▼
┌──────────┐      ┌──────────┐
│ Client2  │────▶ │ API2     │
└──────────┘      └──────────┘
     │                 │
     ▼                 ▼
┌──────────┐      ┌──────────┐
│ Client3  │────▶ │ API3     │
└──────────┘      └──────────┘
     │                 │
     ▼                 ▼
┌──────────┐      ┌──────────┐
│ Client4  │────▶ │ API4     │
└──────────┘      └──────────┘
```"""
    score = layout_spread_reward(
        _completion(response),
        info={"theme": "sequence", "shape_budget": 16},
    )
    assert score <= 0.35
