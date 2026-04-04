FILE: sg194/pipeline_v2/generic_builders.py
LINES: 781-882, 935-1046, 1180-1225

OLD:
```python
    smith_diag = _smith_diagonal(smith_matrix)
    ai_rank = len(smith_diag)
    free_rank = int(bs_rank - ai_rank)
    ...
    return {
        "availability": availability,
        "dBS": bs_rank,
        "dAI": ai_rank if availability == "available" else None,
        "dbs_dai_gap": int(bs_rank - ai_rank) if availability == "available" else None,
        "free_rank": free_rank if availability == "available" else None,
        "classification": classification if availability == "available" else None,
        ...
    }
```

REPLACE WITH:
```python
    smith_diag = _smith_diagonal(smith_matrix)
    ai_image_rank_in_bs = len(smith_diag)
    same_shell_target_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_unknown_vectors])
        if compatible_unknown_vectors
        else sp.zeros(len(unknown_ordering), 0)
    )
    same_shell_target_rank = int(same_shell_target_matrix.rank())
    free_rank = int(bs_rank - ai_image_rank_in_bs)
    ...
    return {
        "availability": availability,
        "dBS": bs_rank,
        "dAI": same_shell_target_rank if availability == "available" else None,
        "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
        "dbs_dai_gap": int(bs_rank - same_shell_target_rank) if availability == "available" else None,
        "dbs_minus_ai_image_rank": int(bs_rank - ai_image_rank_in_bs) if availability == "available" else None,
        "free_rank": free_rank if availability == "available" else None,
        "classification": classification if availability == "available" else None,
        "reported_dai_semantics": "same_shell_target_ai_rank",
        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs",
        "same_shell_rank_check": {
            "dBS": bs_rank if availability == "available" else None,
            "dAI": same_shell_target_rank if availability == "available" else None,
            "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
        },
        ...
    }
```

FILE: sg194/pipeline_v2/generic_builders.py
LINES: 943-1046

OLD:
```python
    same_shell_quotient = _build_same_shell_quotient_from_candidates(...)
    same_shell_available = same_shell_quotient["availability"] == "available"
    exact_alignment_status = (
        "generic_same_shell_target_ready"
        if same_shell_available
        else ...
    )
    ...
    return {
        "availability": "available" if same_shell_available else "blocked",
        "generic_published_classification_ready": same_shell_available,
        "dBS": same_shell_quotient.get("dBS"),
        "dAI": same_shell_quotient.get("dAI"),
        "classification": same_shell_quotient.get("classification"),
        "verification_status": same_shell_quotient.get("verification_status"),
        "evidence": {
            "same_shell_quotient": {...},
            "projected_point_shell_attempt": projected_point_shell_attempt,
        },
    }
```

REPLACE WITH:
```python
    full_current_shell_quotient = _build_same_shell_quotient_from_candidates(...)
    same_shell_available = full_current_shell_quotient["availability"] == "available"
    d_bs = full_current_shell_quotient.get("dBS")
    d_ai = full_current_shell_quotient.get("dAI")
    ai_image_rank_in_bs = full_current_shell_quotient.get("ai_image_rank_in_bs")
    semantic_pass = bool(
        same_shell_available
        and d_bs is not None
        and d_ai is not None
        and d_bs == d_ai
    )
    ...
    return {
        "availability": "available" if semantic_pass else "blocked",
        "generic_published_classification_ready": semantic_pass,
        "dBS": full_current_shell_quotient.get("dBS"),
        "dAI": full_current_shell_quotient.get("dAI"),
        "ai_image_rank_in_bs": full_current_shell_quotient.get("ai_image_rank_in_bs"),
        "classification": full_current_shell_quotient.get("classification"),
        "reported_dai_semantics": full_current_shell_quotient.get("reported_dai_semantics"),
        "classification_derivation_basis": full_current_shell_quotient.get("classification_derivation_basis"),
        "same_shell_semantics": (
            "published_target_object" if semantic_pass else "full_current_shell_diagnostic_object"
        ),
        "quotient_semantics": (
            "same_shell_published_target_quotient" if semantic_pass else "full_current_shell_diagnostic_quotient"
        ),
        "verification_status": (
            "semantic_pass" if semantic_pass else "semantic_fail_dbs_dai_mismatch"
        ),
        "full_current_shell_quotient": full_current_shell_quotient,
        "projected_point_shell_attempt": projected_point_shell_attempt,
        "evidence": {
            "same_shell_rank_check": full_current_shell_quotient.get("same_shell_rank_check"),
            "full_current_shell_quotient": full_current_shell_quotient,
            "projected_point_shell_attempt": projected_point_shell_attempt,
        },
    }
```

FILE: sg194/pipeline_v2/bs_ai.py
LINES: 107-160

OLD:
```python
    if (
        is_target
        and (not benchmark_available)
        and target_spec.generic_builders_expected
        and target_spec.allow_generic_final_without_benchmark
        and target_spec.require_same_shell_target_builder_for_generic_final
        and generic_ready
        and generic_published_ok
        and availability == "available"
        and classification is not None
    ):
        return "generic_final", True, "success"
```

REPLACE WITH:
```python
def _target_semantics_verified(item: dict[str, Any]) -> bool:
    if item.get("availability") != "available":
        return False
    d_bs = item.get("dBS")
    d_ai = item.get("dAI")
    if d_bs is None or d_ai is None:
        return False
    if d_bs != d_ai:
        return False
    if item.get("classification") is None:
        return False
    if item.get("same_shell_semantics") != "published_target_object":
        return False
    if item.get("verification_status") != "semantic_pass":
        return False
    return True

    ...
    semantic_ok = _target_semantics_verified(item)
    if (
        is_target
        and (not benchmark_available)
        and target_spec.generic_builders_expected
        and target_spec.allow_generic_final_without_benchmark
        and target_spec.require_same_shell_target_builder_for_generic_final
        and generic_ready
        and generic_published_ok
        and availability == "available"
        and classification is not None
        and semantic_ok
    ):
        return "generic_final", True, "success"
```

FILE: sg194/pipeline_v2/alignment.py
LINES: 109-155

OLD:
```python
                    "target": {
                        "row_language_kind": "generic_same_shell_published_target",
                        "exact_alignment_status": error_stage,
                        "object_kind": "generic_same_shell_target_object",
                        "availability": "blocked",
                        "generic_builder_ready": False,
                        "generic_published_classification_ready": False,
                        "direct_quotient_status": error_stage,
                        "blocker_stage": error_stage,
                        "blocker_evidence": {},
                        "blocker": fallback_error,
                    },
```

REPLACE WITH:
```python
                    "target": {
                        "row_language_kind": "generic_same_shell_published_target",
                        "exact_alignment_status": error_stage,
                        "object_kind": "generic_same_shell_target_object",
                        "availability": "blocked",
                        "dBS": None,
                        "dAI": None,
                        "ai_image_rank_in_bs": None,
                        "classification": None,
                        "generic_builder_ready": False,
                        "generic_published_classification_ready": False,
                        "reported_dai_semantics": None,
                        "classification_derivation_basis": None,
                        "same_shell_semantics": None,
                        "same_shell_rank_check": {},
                        "verification_status": error_stage,
                        "direct_quotient_status": error_stage,
                        "blocker_stage": error_stage,
                        "blocker_evidence": {},
                        "blocker": fallback_error,
                    },
```
