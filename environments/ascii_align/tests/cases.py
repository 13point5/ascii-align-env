CASE_SPECS = {
    "rect_empty_input": {
        "description": "Empty input should fail minimum rectangle requirement.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_whitespace_only": {
        "description": "Whitespace-only input should fail minimum rectangle requirement.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_single_valid_box": {
        "description": "A valid single box should have no errors.",
        "expected": {
            "correct_rectangles": 1,
            "rectangle_errors": 0,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 0,
        },
    },
    "rect_two_valid_side_by_side": {
        "description": "Two valid boxes side by side should both count.",
        "expected": {
            "correct_rectangles": 2,
            "rectangle_errors": 0,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 0,
        },
    },
    "rect_nested_valid": {
        "description": "Nested boxes should both count as valid rectangles.",
        "expected": {
            "correct_rectangles": 2,
            "rectangle_errors": 0,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 0,
        },
    },
    "rect_missing_bottom_right_corner": {
        "description": "A box missing its bottom-right closure should fail rectangle validation.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_right_edge_shifted": {
        "description": "A shifted right edge should produce a rectangle error.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_top_edge_gap": {
        "description": "A top-edge gap should fail closure.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_mixed_one_valid_one_invalid": {
        "description": "One valid and one invalid box should split into one success and one rectangle error.",
        "expected": {
            "correct_rectangles": 1,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "rect_no_rectangle_text_only": {
        "description": "Text-only diagram should fail minimum rectangle requirement.",
        "expected": {
            "correct_rectangles": 0,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "regression_user_flowchart_case": {
        "description": "Provided flowchart regression should not receive full score.",
        "expected": {"misaligned_min": 1, "connector_errors_min": 1},
    },
    "regression_user_sequence_case": {
        "description": "Provided sequence regression should not receive full score.",
        "expected": {"misaligned_min": 1, "connector_errors_min": 1},
    },
    "regression_policy_diagram_current": {
        "description": "Current policy diagram should match expected mixed error profile.",
        "expected": {
            "correct_rectangles": 10,
            "rectangle_errors": 1,
            "connector_errors": 1,
            "arrow_errors": 0,
            "misaligned": 2,
        },
    },
    "regression_policy_diagram_fix_dangling_queue_line": {
        "description": "Fixing dangling queue line should remove connector error only.",
        "expected": {
            "correct_rectangles": 10,
            "rectangle_errors": 1,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "regression_policy_diagram_fix_logging_box_only": {
        "description": "Fixing logging box only should leave connector issue unchanged.",
        "expected": {
            "correct_rectangles": 11,
            "rectangle_errors": 0,
            "connector_errors": 1,
            "arrow_errors": 0,
            "misaligned": 1,
        },
    },
    "regression_policy_diagram_fix_all": {
        "description": "Fixing both logging box and queue connector should fully pass.",
        "expected": {
            "correct_rectangles": 11,
            "rectangle_errors": 0,
            "connector_errors": 0,
            "arrow_errors": 0,
            "misaligned": 0,
        },
    },
}

