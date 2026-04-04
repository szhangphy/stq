diff --git a/sg194/pipeline_v2/alignment.py b/sg194/pipeline_v2/alignment.py
index 095b074..6cdc988 100644
--- a/sg194/pipeline_v2/alignment.py
+++ b/sg194/pipeline_v2/alignment.py
@@ -100,62 +100,74 @@ def build_alignment_summary(spec: GroupSpec, adapter, artifacts: dict[str, Any])
                     "error": fallback_error,
                 },
                 "single": {
                     "raw": {
                         "row_language_kind": current_row_shell["row_language_kind"],
                         "exact_alignment_status": "not_applicable_current_row_shell_only",
                         "object_kind": "generic_current_row_shell",
                         "availability": "available",
                     },
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
+                        "reported_dbs_semantics": None,
                         "reported_dai_semantics": None,
                         "classification_derivation_basis": None,
+                        "object_semantics": None,
                         "same_shell_semantics": None,
+                        "quotient_semantics": None,
+                        "promotion_reason": None,
                         "same_shell_rank_check": {},
                         "verification_status": error_stage,
+                        "full_current_shell_quotient": None,
+                        "projected_point_shell_attempt": None,
                         "direct_quotient_status": error_stage,
                         "blocker_stage": error_stage,
                         "blocker_evidence": {},
                         "blocker": fallback_error,
                     },
                 },
                 "double": {
                     "raw": {
                         "row_language_kind": current_row_shell["row_language_kind"],
                         "exact_alignment_status": "not_applicable_current_row_shell_only",
                         "object_kind": "generic_current_row_shell",
                         "availability": "available",
                     },
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
+                        "reported_dbs_semantics": None,
                         "reported_dai_semantics": None,
                         "classification_derivation_basis": None,
+                        "object_semantics": None,
                         "same_shell_semantics": None,
+                        "quotient_semantics": None,
+                        "promotion_reason": None,
                         "same_shell_rank_check": {},
                         "verification_status": error_stage,
+                        "full_current_shell_quotient": None,
+                        "projected_point_shell_attempt": None,
                         "direct_quotient_status": error_stage,
                         "blocker_stage": error_stage,
                         "blocker_evidence": {},
                         "blocker": fallback_error,
                     },
                 },
             }
     return adapter.build_alignment_summary(spec, artifacts)
diff --git a/sg194/pipeline_v2/bs_ai.py b/sg194/pipeline_v2/bs_ai.py
index f373da0..ef77b49 100644
--- a/sg194/pipeline_v2/bs_ai.py
+++ b/sg194/pipeline_v2/bs_ai.py
@@ -68,42 +68,44 @@ def _build_generic_result_objects(
                 "ai_image_rank_in_bs": target_alignment.get("ai_image_rank_in_bs"),
                 "dbs_minus_ai_image_rank": target_alignment.get("dbs_minus_ai_image_rank"),
                 "classification": target_alignment.get("classification"),
                 "free_rank": target_alignment.get("free_rank"),
                 "finite_part": list(target_alignment.get("finite_part", [])),
                 "quotient_derivation_mode": target_alignment.get(
                     "direct_quotient_status",
                     "blocked_missing_generic_direct_quotient_builder",
                 ),
                 "exact_alignment_status": target_alignment.get(
                     "exact_alignment_status",
                     "blocked_missing_generic_current_row_compatibility_builder",
                 ),
                 "current_row_shell_status": current_row_status,
                 "local_ai_seed_status": local_ai_status,
                 "quotient_prerequisites_status": quotient_prereq_status,
                 "generic_builder_ready": bool(target_alignment.get("generic_builder_ready", False)),
                 "generic_published_classification_ready": bool(
                     target_alignment.get("generic_published_classification_ready", False)
                 ),
+                "reported_dbs_semantics": target_alignment.get("reported_dbs_semantics"),
                 "reported_dai_semantics": target_alignment.get("reported_dai_semantics"),
                 "classification_derivation_basis": target_alignment.get("classification_derivation_basis"),
+                "object_semantics": target_alignment.get("object_semantics"),
                 "same_shell_semantics": target_alignment.get("same_shell_semantics"),
                 "quotient_semantics": target_alignment.get("quotient_semantics"),
                 "promotion_reason": target_alignment.get("promotion_reason"),
                 "same_shell_rank_check": target_alignment.get("same_shell_rank_check"),
                 "full_current_shell_quotient": target_alignment.get("full_current_shell_quotient"),
                 "projected_point_shell_attempt": target_alignment.get("projected_point_shell_attempt"),
                 "blocker_stage": target_alignment.get("blocker_stage"),
                 "blocker_evidence": target_alignment.get("blocker_evidence"),
                 "direct_quotient_status": target_alignment.get("direct_quotient_status"),
                 "verification_status": target_alignment.get("verification_status"),
                 "blocker": target_alignment.get("blocker", blocked),
                 "source_files": [],
             }
         )
     return records
 
 
 def _target_semantics_verified(item: dict[str, Any]) -> bool:
     if item.get("availability") != "available":
         return False
@@ -224,42 +226,44 @@ def build_bs_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str
                 "object_id": item["object_id"],
                 "mode": item["mode"],
                 "row_language_level": item["row_language_level"],
                 "row_language_kind": item["row_language_kind"],
                 "object_kind": item["object_kind"],
                 "availability": item["availability"],
                 "dBS": item["dBS"],
                 "ai_image_rank_in_bs": item.get("ai_image_rank_in_bs"),
                 "generic_builder_ready": item.get("generic_builder_ready"),
                 "generic_published_classification_ready": item.get(
                     "generic_published_classification_ready"
                 ),
                 "exact_alignment_status": item.get("exact_alignment_status"),
                 "final_result_mode": item.get("final_result_mode"),
                 "classification_is_published_final": item.get("classification_is_published_final"),
                 "status": item.get("status"),
                 "blocker_stage": item.get("blocker_stage"),
                 "blocker_evidence": item.get("blocker_evidence"),
                 "direct_quotient_status": item.get("direct_quotient_status"),
                 "classification": item.get("classification"),
+                "reported_dbs_semantics": item.get("reported_dbs_semantics"),
                 "reported_dai_semantics": item.get("reported_dai_semantics"),
                 "classification_derivation_basis": item.get("classification_derivation_basis"),
+                "object_semantics": item.get("object_semantics"),
                 "same_shell_semantics": item.get("same_shell_semantics"),
                 "quotient_semantics": item.get("quotient_semantics"),
                 "promotion_reason": item.get("promotion_reason"),
                 "same_shell_rank_check": item.get("same_shell_rank_check"),
                 "verification_status": item.get("verification_status"),
                 "blocker": item.get("blocker"),
             }
             for item in records
         ],
     }
 
 
 def build_ai_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
     return {
         "generated_at": now_iso(),
         "group": spec.group_id,
         "builder_prerequisites": [
             {
                 "object_id": item["object_id"],
                 "current_row_shell_status": item.get("current_row_shell_status"),
@@ -274,32 +278,34 @@ def build_ai_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str
                 "object_id": item["object_id"],
                 "mode": item["mode"],
                 "row_language_level": item["row_language_level"],
                 "row_language_kind": item["row_language_kind"],
                 "object_kind": item["object_kind"],
                 "availability": item["availability"],
                 "dAI": item["dAI"],
                 "ai_image_rank_in_bs": item.get("ai_image_rank_in_bs"),
                 "generic_builder_ready": item.get("generic_builder_ready"),
                 "generic_published_classification_ready": item.get(
                     "generic_published_classification_ready"
                 ),
                 "exact_alignment_status": item.get("exact_alignment_status"),
                 "final_result_mode": item.get("final_result_mode"),
                 "classification_is_published_final": item.get("classification_is_published_final"),
                 "status": item.get("status"),
                 "blocker_stage": item.get("blocker_stage"),
                 "blocker_evidence": item.get("blocker_evidence"),
                 "direct_quotient_status": item.get("direct_quotient_status"),
                 "classification": item.get("classification"),
+                "reported_dbs_semantics": item.get("reported_dbs_semantics"),
                 "reported_dai_semantics": item.get("reported_dai_semantics"),
                 "classification_derivation_basis": item.get("classification_derivation_basis"),
+                "object_semantics": item.get("object_semantics"),
                 "same_shell_semantics": item.get("same_shell_semantics"),
                 "quotient_semantics": item.get("quotient_semantics"),
                 "promotion_reason": item.get("promotion_reason"),
                 "same_shell_rank_check": item.get("same_shell_rank_check"),
                 "verification_status": item.get("verification_status"),
                 "blocker": item.get("blocker"),
             }
             for item in records
         ],
     }
diff --git a/sg194/pipeline_v2/generic_builders.py b/sg194/pipeline_v2/generic_builders.py
index b8c36bb..012c231 100644
--- a/sg194/pipeline_v2/generic_builders.py
+++ b/sg194/pipeline_v2/generic_builders.py
@@ -677,63 +677,69 @@ def _build_quotient_from_candidates(
                     "family_letter": candidate.get("family_letter"),
                     "reason": f"target_point_shell_embedding_failed: {exc}",
                 }
             )
     ai_in_bs = sp.Matrix(coords).T if coords else sp.zeros(bs_rank, 0)
     smith_data = port.swyckoff_k.smith_normal_form([[int(value) for value in row] for row in ai_in_bs.tolist()])
     smith_matrix = sp.Matrix(smith_data[0]) if ai_in_bs.cols else sp.zeros(bs_rank, 0)
     smith_diag = _smith_diagonal(smith_matrix)
     ai_image_rank_in_bs = len(smith_diag)
     projected_ai_matrix = (
         sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_point_vectors])
         if compatible_point_vectors
         else sp.zeros(len(point_unknown_ordering), 0)
     )
     projected_target_ai_rank = int(projected_ai_matrix.rank())
     surviving_finite_part = [value for value in smith_diag if value > 1]
     surviving_free_rank = int(bs_rank - ai_image_rank_in_bs)
     surviving_classification = _quotient_group_string(surviving_free_rank, surviving_finite_part)
     final_available = not (rejected_candidates or embedding_failures or induced["failure_count"])
     return {
+        "object_semantics": "projected_point_shell_diagnostic_quotient",
         "dBS": bs_rank,
-        "dAI": projected_target_ai_rank if final_available else None,
+        "dAI": None,
         "ai_image_rank_in_bs": ai_image_rank_in_bs if final_available else None,
-        "dbs_dai_gap": int(bs_rank - projected_target_ai_rank) if final_available else None,
+        "projected_target_ai_rank": projected_target_ai_rank if final_available else None,
+        "dbs_dai_gap": None,
         "dbs_minus_ai_image_rank": int(bs_rank - ai_image_rank_in_bs) if final_available else None,
         "free_rank": surviving_free_rank if final_available else None,
         "finite_part": surviving_finite_part if final_available else [],
         "classification": surviving_classification if final_available else None,
         "surviving_ai_rank": ai_image_rank_in_bs,
         "surviving_dbs_ai_gap": int(bs_rank - ai_image_rank_in_bs),
         "surviving_free_rank": surviving_free_rank,
         "surviving_finite_part": surviving_finite_part,
         "surviving_classification": surviving_classification,
         "final_dai_available": final_available,
         "smith_diagonal_nonzero": smith_diag,
-        "reported_dai_semantics": "projected_point_shell_ai_rank",
-        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs",
+        "reported_dbs_semantics": "projected_point_shell_rank",
+        "reported_dai_semantics": "unresolved_do_not_promote_to_target",
+        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs_on_projected_point_shell",
         "same_shell_semantics": "diagnostic_projected_point_shell_attempt",
-        "quotient_semantics": "projected_point_shell_diagnostic_object",
+        "quotient_semantics": "projected_point_shell_diagnostic_quotient",
         "same_shell_rank_check": {
             "dBS": bs_rank if final_available else None,
-            "dAI": projected_target_ai_rank if final_available else None,
+            "dAI": None,
             "ai_image_rank_in_bs": ai_image_rank_in_bs if final_available else None,
+            "diagnostic_projected_target_ai_rank": (
+                projected_target_ai_rank if final_available else None
+            ),
         },
         "ai_candidate_count": induced["candidate_count"],
         "ai_candidate_count_used": len(compatible_candidates),
         "ai_failure_count": induced["failure_count"],
         "ai_incompatible_count": len(rejected_candidates),
         "ai_embedding_failure_count": len(embedding_failures),
         "ai_incompatible_candidates": rejected_candidates,
         "ai_embedding_failures": embedding_failures,
         "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
         "compatibility_check_mode": "point_shell_projection_over_full_kernel_basis",
         "full_shell_rank": full_bs_rank,
         "point_shell_rank": bs_rank,
         "point_unknown_count": len(point_unknown_ordering),
         "point_unknown_ordering": point_unknown_ordering,
         "native_target_point_ids": list(point_ids),
     }
 
 
 def _structured_projection_rank_loss(message: str) -> dict[str, Any]:
     match = re.search(r"\(full=(\d+), point=(\d+)\)", message)
@@ -827,76 +833,99 @@ def _build_same_shell_quotient_from_candidates(
         sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_unknown_vectors])
         if compatible_unknown_vectors
         else sp.zeros(len(unknown_ordering), 0)
     )
     same_shell_target_rank = int(same_shell_target_matrix.rank())
     free_rank = int(bs_rank - ai_image_rank_in_bs)
     finite_part = [value for value in smith_diag if value > 1]
     classification = _quotient_group_string(free_rank, finite_part)
     availability = "available" if not embedding_failures and not induced["failure_count"] else "blocked"
     blocker = None
     blocker_stage = None
     if induced["failure_count"]:
         blocker_stage = "generic_same_shell_target_induction_failure"
         blocker = (
             "generic same-shell target induction failed for one or more local-library generators"
         )
     elif embedding_failures:
         blocker_stage = "generic_same_shell_target_embedding_failure"
         blocker = "generic same-shell target AI-in-BS embedding failed for at least one compatibility-zero candidate"
     return {
+        "object_semantics": "full_current_shell_diagnostic_quotient",
         "availability": availability,
         "blocker_stage": blocker_stage,
         "blocker": blocker,
         "dBS": bs_rank,
-        "dAI": same_shell_target_rank if availability == "available" else None,
+        "dAI": None,
         "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
-        "dbs_dai_gap": int(bs_rank - same_shell_target_rank) if availability == "available" else None,
+        "same_shell_candidate_ai_rank": (
+            same_shell_target_rank if availability == "available" else None
+        ),
+        "dbs_dai_gap": None,
         "dbs_minus_ai_image_rank": int(bs_rank - ai_image_rank_in_bs) if availability == "available" else None,
         "free_rank": free_rank if availability == "available" else None,
         "finite_part": finite_part if availability == "available" else [],
         "classification": classification if availability == "available" else None,
         "smith_diagonal_nonzero": smith_diag,
-        "reported_dai_semantics": "same_shell_target_ai_rank",
-        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs",
+        "reported_dbs_semantics": "full_current_shell_rank",
+        "reported_dai_semantics": "ai_rank_placeholder_do_not_treat_as_published_target",
+        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs_on_full_current_shell",
         "same_shell_rank_check": {
             "dBS": bs_rank if availability == "available" else None,
-            "dAI": same_shell_target_rank if availability == "available" else None,
+            "dAI": None,
             "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
+            "diagnostic_same_shell_candidate_ai_rank": (
+                same_shell_target_rank if availability == "available" else None
+            ),
         },
         "ai_candidate_count": induced["candidate_count"],
         "ai_candidate_count_used": len(compatible_candidates),
         "ai_failure_count": induced["failure_count"],
         "ai_incompatible_count": len(rejected_candidates),
         "ai_embedding_failure_count": len(embedding_failures),
         "ai_incompatible_candidates": rejected_candidates,
         "ai_embedding_failures": embedding_failures,
         "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
         "compatibility_check_mode": "same_shell_full_current_rows_over_full_kernel_basis",
         "target_unknown_count": len(unknown_ordering),
         "target_unknown_ordering": list(unknown_ordering),
         "verification_status": (
-            "generic_same_shell_target_verified_from_current_shell_compatibility_zero_subset"
+            "generic_same_shell_diagnostic_quotient_available"
             if availability == "available"
             else "generic_same_shell_target_pending_manual_followup"
         ),
+        "same_shell_semantics": "full_current_shell_diagnostic_object",
+        "quotient_semantics": "full_current_shell_diagnostic_quotient",
+    }
+
+
+def _same_shell_published_target_ready(
+    *,
+    same_shell_candidate: dict[str, Any],
+    projected_point_shell_attempt: dict[str, Any],
+) -> tuple[bool, str, dict[str, Any]]:
+    evidence = {
+        "same_shell_candidate_semantics": same_shell_candidate.get("object_semantics"),
+        "projected_point_shell_status": projected_point_shell_attempt.get("status"),
+        "projected_point_shell_blocker_stage": projected_point_shell_attempt.get("blocker_stage"),
     }
+    return False, "same_shell_candidate_is_still_diagnostic_not_published_target", evidence
 
 
 def _attempt_projected_point_shell_quotient(
     point_ids: list[str],
     unknown_ordering: list[str],
     bs_analysis: dict[str, Any],
     compatibility: dict[str, Any],
     induced: dict[str, Any],
 ) -> dict[str, Any]:
     try:
         quotient = _build_quotient_from_candidates(
             point_ids,
             unknown_ordering,
             bs_analysis,
             compatibility,
             induced,
         )
         return {
             "status": "available",
             "attempt_kind": "projected_point_shell",
@@ -930,131 +959,130 @@ def _attempt_projected_point_shell_quotient(
             "evidence": evidence,
             "raw_error": message,
         }
 
 
 def _build_generic_same_shell_target_object(
     *,
     group_id: str,
     mode: str,
     compatibility: dict[str, Any],
     bs_analysis: dict[str, Any],
     induced: dict[str, Any],
     projected_point_shell_attempt: dict[str, Any],
 ) -> dict[str, Any]:
     full_current_shell_quotient = _build_same_shell_quotient_from_candidates(
         bs_analysis["unknown_ordering"],
         bs_analysis,
         compatibility,
         induced,
     )
-    same_shell_available = full_current_shell_quotient["availability"] == "available"
-    d_bs = full_current_shell_quotient.get("dBS")
-    d_ai = full_current_shell_quotient.get("dAI")
-    ai_image_rank_in_bs = full_current_shell_quotient.get("ai_image_rank_in_bs")
-    semantic_pass = bool(
-        same_shell_available
-        and d_bs is not None
-        and d_ai is not None
-        and d_bs == d_ai
+    semantic_pass, promotion_reason, semantic_evidence = _same_shell_published_target_ready(
+        same_shell_candidate=full_current_shell_quotient,
+        projected_point_shell_attempt=projected_point_shell_attempt,
     )
-    blocker = None
-    blocker_stage = None
-    if semantic_pass:
-        availability = "available"
-        exact_alignment_status = "generic_same_shell_target_ready"
-        target_alignment_builder_status = "available"
-        direct_quotient_status = "generic_same_shell_direct_quotient_success"
-        verification_status = "semantic_pass"
-        same_shell_semantics = "published_target_object"
-        quotient_semantics = "same_shell_published_target_quotient"
-        promotion_reason = "same_shell_published_target_semantics_verified"
-    elif same_shell_available:
-        availability = "blocked"
-        blocker_stage = "generic_same_shell_target_semantic_guard_failed"
-        blocker = (
-            "generic same-shell target candidate remains semantically ambiguous: "
-            f"dBS={d_bs}, dAI={d_ai}, ai_image_rank_in_bs={ai_image_rank_in_bs}"
-        )
-        exact_alignment_status = blocker_stage
-        target_alignment_builder_status = "blocked"
-        direct_quotient_status = blocker_stage
-        verification_status = "semantic_fail_dbs_dai_mismatch"
-        same_shell_semantics = "full_current_shell_diagnostic_object"
-        quotient_semantics = "full_current_shell_diagnostic_quotient"
-        promotion_reason = None
-    else:
-        availability = "blocked"
-        blocker_stage = (
-            full_current_shell_quotient.get("blocker_stage")
-            or projected_point_shell_attempt.get("blocker_stage")
-            or "generic_same_shell_target_blocked"
-        )
-        blocker = (
-            full_current_shell_quotient.get("blocker")
-            or projected_point_shell_attempt.get("blocker")
-            or "generic same-shell target builder blocked"
-        )
-        exact_alignment_status = blocker_stage
-        target_alignment_builder_status = "blocked"
-        direct_quotient_status = blocker_stage
-        verification_status = full_current_shell_quotient.get("verification_status")
-        same_shell_semantics = "full_current_shell_diagnostic_object"
-        quotient_semantics = "full_current_shell_diagnostic_quotient"
-        promotion_reason = None
+
+    if not semantic_pass:
+        blocker_evidence = {
+            **semantic_evidence,
+            "full_current_shell_quotient": full_current_shell_quotient,
+            "projected_point_shell_attempt": projected_point_shell_attempt,
+        }
+        return {
+            "object_id": f"{mode}_target_same_shell",
+            "group": group_id,
+            "mode": mode,
+            "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
+            "object_kind": GENERIC_TARGET_OBJECT_KIND,
+            "availability": "blocked",
+            "exact_alignment_status": "generic_same_shell_target_semantics_fail",
+            "generic_builder_ready": True,
+            "generic_published_classification_ready": False,
+            "target_alignment_builder_status": "blocked",
+            "direct_quotient_status": "generic_same_shell_target_semantics_fail",
+            "local_ai_embedding_status": (
+                "same_shell_full_current_row_embedding_success"
+                if full_current_shell_quotient.get("availability") == "available"
+                else "same_shell_full_current_row_embedding_blocked"
+            ),
+            "dBS": None,
+            "dAI": None,
+            "ai_image_rank_in_bs": full_current_shell_quotient.get("ai_image_rank_in_bs"),
+            "dbs_dai_gap": None,
+            "dbs_minus_ai_image_rank": full_current_shell_quotient.get("dbs_minus_ai_image_rank"),
+            "free_rank": None,
+            "finite_part": [],
+            "classification": None,
+            "smith_diagonal_nonzero": list(full_current_shell_quotient.get("smith_diagonal_nonzero", [])),
+            "object_semantics": "generic_same_shell_target_object_blocked_before_published_semantics",
+            "reported_dbs_semantics": None,
+            "reported_dai_semantics": "unresolved_do_not_promote_to_target",
+            "classification_derivation_basis": None,
+            "same_shell_semantics": "not_yet_published_target_object",
+            "quotient_semantics": "blocked_before_published_target_semantics",
+            "promotion_reason": promotion_reason,
+            "same_shell_rank_check": None,
+            "verification_status": "semantic_fail",
+            "source": "generic_symmetry_ops_same_shell_target_builder",
+            "blocker_stage": "generic_same_shell_target_semantics_fail",
+            "blocker": "same-shell quotient is still a diagnostic object and cannot yet be promoted to a published target object",
+            "blocker_evidence": blocker_evidence,
+            "full_current_shell_quotient": full_current_shell_quotient,
+            "projected_point_shell_attempt": projected_point_shell_attempt,
+            "evidence": blocker_evidence,
+            "quotient": full_current_shell_quotient,
+        }
 
     return {
         "object_id": f"{mode}_target_same_shell",
         "group": group_id,
         "mode": mode,
         "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
         "object_kind": GENERIC_TARGET_OBJECT_KIND,
-        "availability": availability,
-        "exact_alignment_status": exact_alignment_status,
+        "availability": "available",
+        "exact_alignment_status": "generic_same_shell_target_ready",
         "generic_builder_ready": True,
-        "generic_published_classification_ready": semantic_pass,
-        "target_alignment_builder_status": target_alignment_builder_status,
-        "direct_quotient_status": direct_quotient_status,
-        "local_ai_embedding_status": (
-            "same_shell_full_current_row_embedding_success"
-            if same_shell_available
-            else "same_shell_full_current_row_embedding_blocked"
-        ),
+        "generic_published_classification_ready": True,
+        "target_alignment_builder_status": "available",
+        "direct_quotient_status": "generic_same_shell_direct_quotient_success",
+        "local_ai_embedding_status": "same_shell_full_current_row_embedding_success",
         "dBS": full_current_shell_quotient.get("dBS"),
         "dAI": full_current_shell_quotient.get("dAI"),
         "ai_image_rank_in_bs": full_current_shell_quotient.get("ai_image_rank_in_bs"),
         "dbs_dai_gap": full_current_shell_quotient.get("dbs_dai_gap"),
         "dbs_minus_ai_image_rank": full_current_shell_quotient.get("dbs_minus_ai_image_rank"),
         "free_rank": full_current_shell_quotient.get("free_rank"),
         "finite_part": list(full_current_shell_quotient.get("finite_part", [])),
         "classification": full_current_shell_quotient.get("classification"),
         "smith_diagonal_nonzero": list(full_current_shell_quotient.get("smith_diagonal_nonzero", [])),
+        "object_semantics": "published_target_object",
+        "reported_dbs_semantics": full_current_shell_quotient.get("reported_dbs_semantics"),
         "reported_dai_semantics": full_current_shell_quotient.get("reported_dai_semantics"),
         "classification_derivation_basis": full_current_shell_quotient.get("classification_derivation_basis"),
-        "same_shell_semantics": same_shell_semantics,
-        "quotient_semantics": quotient_semantics,
+        "same_shell_semantics": "published_target_object",
+        "quotient_semantics": "same_shell_published_target_quotient",
         "promotion_reason": promotion_reason,
         "same_shell_rank_check": full_current_shell_quotient.get("same_shell_rank_check"),
-        "verification_status": verification_status,
+        "verification_status": "semantic_pass",
         "source": "generic_symmetry_ops_same_shell_target_builder",
-        "blocker_stage": blocker_stage,
-        "blocker": blocker,
+        "blocker_stage": None,
+        "blocker": None,
         "full_current_shell_quotient": full_current_shell_quotient,
         "projected_point_shell_attempt": projected_point_shell_attempt,
         "evidence": {
             "same_shell_rank_check": full_current_shell_quotient.get("same_shell_rank_check"),
             "full_current_shell_quotient": full_current_shell_quotient,
             "projected_point_shell_attempt": projected_point_shell_attempt,
         },
         "quotient": full_current_shell_quotient,
     }
 
 
 def _generic_progress_payload(
     group_id: str,
     mode: str,
     builder_variant: str,
     *,
     shared: dict[str, Any] | None = None,
     compatibility: dict[str, Any] | None = None,
     local_library: dict[str, Any] | None = None,
     induced: dict[str, Any] | None = None,
@@ -1247,41 +1275,41 @@ def generic_mode_progress(group_id: str, mode: str, builder_variant: str = "auth
         and same_shell_target.get("dAI") is not None
     )
     if semantic_ready:
         return _generic_progress_payload(
             group_id,
             mode,
             builder_variant,
             shared=shared,
             compatibility=compatibility,
             local_library=local_library,
             induced=induced,
             quotient=same_shell_target.get("quotient"),
             same_shell_target=same_shell_target,
             blocker_stage=None,
             blocker=None,
             current_row_shell_status="available",
             local_ai_seed_status="available",
             compatibility_builder_status="available",
             target_alignment_builder_status="available",
             generic_builder_ready=True,
-            generic_published_classification_ready=True,
+            generic_published_classification_ready=semantic_ready,
         )
 
     return _generic_progress_payload(
         group_id,
         mode,
         builder_variant,
         shared=shared,
         compatibility=compatibility,
         local_library=local_library,
         induced=induced,
         quotient=same_shell_target.get("quotient"),
         same_shell_target=same_shell_target,
         blocker_stage=same_shell_target.get("blocker_stage"),
         blocker=same_shell_target.get("blocker"),
         current_row_shell_status="available",
         local_ai_seed_status="available",
         compatibility_builder_status="available",
         target_alignment_builder_status=same_shell_target.get("target_alignment_builder_status", "blocked"),
         generic_builder_ready=bool(same_shell_target.get("generic_builder_ready", False)),
         generic_published_classification_ready=semantic_ready,
@@ -1430,64 +1458,66 @@ def generic_alignment_summary(group_id: str) -> dict[str, Any]:
                     else "blocked_before_projected_point_shell_embedding"
                 ),
             ),
             "direct_quotient_status": target.get(
                 "direct_quotient_status",
                 (
                     "diagnostic_only_projected_point_shell"
                     if quotient
                     else progress.get("blocker_stage")
                 ),
             ),
             "ai_candidate_count": progress.get("ai_candidate_count"),
             "ai_failure_count": progress.get("ai_failure_count"),
             "dBS": target.get("dBS"),
             "dAI": target.get("dAI"),
             "ai_image_rank_in_bs": target.get("ai_image_rank_in_bs"),
             "dbs_minus_ai_image_rank": target.get("dbs_minus_ai_image_rank"),
             "classification": target.get("classification"),
             "free_rank": target.get("free_rank"),
             "finite_part": list(target.get("finite_part", [])),
+            "reported_dbs_semantics": target.get("reported_dbs_semantics"),
             "reported_dai_semantics": target.get("reported_dai_semantics"),
             "classification_derivation_basis": target.get("classification_derivation_basis"),
+            "object_semantics": target.get("object_semantics"),
             "same_shell_semantics": target.get("same_shell_semantics"),
             "quotient_semantics": target.get("quotient_semantics"),
             "promotion_reason": target.get("promotion_reason"),
             "same_shell_rank_check": target.get("same_shell_rank_check"),
             "verification_status": target.get("verification_status"),
             "full_current_shell_quotient": target.get("full_current_shell_quotient"),
             "projected_point_shell_attempt": target.get("projected_point_shell_attempt"),
             "diagnostic_projected_point_shell_status": projected.get("status"),
             "diagnostic_projected_point_shell_blocker_stage": projected.get("blocker_stage"),
             "diagnostic_projected_point_shell_blocker": projected.get("blocker"),
             "diagnostic_projected_point_shell_evidence": projected.get("evidence"),
             "diagnostic_projected_point_shell_dbs": (projected.get("quotient") or {}).get("dBS"),
             "diagnostic_projected_point_shell_dai": (projected.get("quotient") or {}).get("dAI"),
             "diagnostic_projected_point_shell_ai_image_rank_in_bs": (projected.get("quotient") or {}).get("ai_image_rank_in_bs"),
             "diagnostic_projected_point_shell_classification": (projected.get("quotient") or {}).get("classification"),
             "generic_builder_ready": progress.get("generic_builder_ready", False),
             "generic_published_classification_ready": progress.get(
                 "generic_published_classification_ready", False
             ),
             "blocker_stage": target.get("blocker_stage", progress.get("blocker_stage")),
             "blocker": target.get("blocker", progress.get("blocker")),
-            "blocker_evidence": target.get("evidence"),
+            "blocker_evidence": target.get("blocker_evidence", target.get("evidence")),
         }
 
     current_row_shell = {
         "status": "available",
         "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
         "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
         "point_count": len(shared["target_point_ids"]),
         "point_ids": list(shared["target_point_ids"]),
     }
     local_ai_seed_builder = {
         "status": "available",
         "row_language_kind": "generic_local_ai_seed_from_site_symmetry_data",
         "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
         "realspace_wyckoff_family_count": single_progress.get("local_ai_family_count"),
     }
     return {
         "generated_at": now_iso(),
         "group": group_id,
         "trust_policy": "symmetry_operations_only",
         "current_row_shell": current_row_shell,
@@ -1599,57 +1629,59 @@ def generic_result_objects(group_id: str, builder_variant: str = "authoritative"
                 "direct_quotient_status": target.get(
                     "direct_quotient_status",
                     (
                         "diagnostic_only_projected_point_shell"
                         if quotient
                         else progress.get("blocker_stage")
                     ),
                 ),
                 "verification_status": target.get(
                     "verification_status",
                     "blocked_projected_point_shell_result_not_published_as_active_object",
                 ),
                 "ai_candidate_count": progress.get("ai_candidate_count"),
                 "ai_candidate_count_used": quotient.get("ai_candidate_count_used"),
                 "ai_failure_count": progress.get("ai_failure_count"),
                 "ai_incompatible_count": quotient.get("ai_incompatible_count"),
                 "ai_embedding_failure_count": quotient.get("ai_embedding_failure_count"),
                 "dbs_dai_gap": quotient.get("dbs_dai_gap"),
                 "dbs_minus_ai_image_rank": quotient.get("dbs_minus_ai_image_rank"),
                 "smith_diagonal_nonzero": quotient.get("smith_diagonal_nonzero"),
+                "reported_dbs_semantics": target.get("reported_dbs_semantics"),
                 "reported_dai_semantics": target.get("reported_dai_semantics"),
                 "classification_derivation_basis": target.get("classification_derivation_basis"),
+                "object_semantics": target.get("object_semantics"),
                 "same_shell_semantics": target.get("same_shell_semantics"),
                 "quotient_semantics": target.get("quotient_semantics"),
                 "promotion_reason": target.get("promotion_reason"),
                 "same_shell_rank_check": target.get("same_shell_rank_check"),
                 "full_current_shell_quotient": target.get("full_current_shell_quotient"),
                 "projected_point_shell_attempt": target.get("projected_point_shell_attempt"),
                 "ai_incompatible_candidates": quotient.get("ai_incompatible_candidates", []),
                 "ai_embedding_failures": quotient.get("ai_embedding_failures", []),
                 "ai_filter_mode": quotient.get(
                     "compatibility_check_mode",
                     "diagnostic_point_shell_projection_over_full_kernel_basis",
                 ),
                 "blocker": target.get("blocker", progress.get("blocker")),
                 "blocker_stage": target.get("blocker_stage", progress.get("blocker_stage")),
-                "blocker_evidence": target.get("evidence"),
+                "blocker_evidence": target.get("blocker_evidence", target.get("evidence")),
                 "generic_builder_ready": progress.get("generic_builder_ready", False),
                 "generic_published_classification_ready": progress.get(
                     "generic_published_classification_ready", False
                 ),
                 "diagnostic_projected_point_shell_status": projected.get("status"),
                 "diagnostic_projected_point_shell_blocker_stage": projected.get("blocker_stage"),
                 "diagnostic_projected_point_shell_blocker": projected.get("blocker"),
                 "diagnostic_projected_point_shell_evidence": projected.get("evidence"),
                 "diagnostic_projected_point_shell_dbs": (projected.get("quotient") or {}).get("dBS"),
                 "diagnostic_projected_point_shell_dai": (projected.get("quotient") or {}).get("dAI"),
                 "diagnostic_projected_point_shell_ai_image_rank_in_bs": (projected.get("quotient") or {}).get("ai_image_rank_in_bs"),
                 "diagnostic_projected_point_shell_classification": (projected.get("quotient") or {}).get("classification"),
                 "source": target.get("source", "generic_symmetry_ops_same_shell_target_builder"),
                 "source_files": [
                     str(RUNTIME_BACKEND.relative_to(ROOT.parent)),
                     str(LOCAL_IRREP_BACKEND.relative_to(ROOT.parent)),
                 ],
             }
         )
     return results
