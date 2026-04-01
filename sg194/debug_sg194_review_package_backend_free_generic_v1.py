#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = ROOT / "review_package_sg194_backend_free_generic_v1"
PACKAGE_TAR = ROOT / "review_package_sg194_backend_free_generic_v1.tar.gz"

COPY_LAYOUT = {
    "purity_layer": [
        "sg194_generic_path_purity_audit_v1.json",
        "sg194_generic_path_purity_audit_v1.md",
        "sg194_backend_dependency_cut_v1.json",
        "sg194_backend_dependency_cut_v1.md",
    ],
    "generality_layer": [
        "sg194_generality_verdict_v3.json",
        "sg194_generality_verdict_v3.md",
        "sg194_case_by_case_map_v3.json",
        "sg194_case_by_case_map_v3.md",
    ],
    "generic_194_layer": [
        "sg194_194_special_to_generic_map_v1.json",
        "sg194_194_special_to_generic_map_v1.md",
        "sg194_194_generic_regression_v1.json",
        "sg194_194_generic_regression_v1.md",
        "sg194_194_single_generic_final_result_v1.json",
        "sg194_194_single_generic_final_result_v1.md",
        "sg194_194_double_generic_final_result_v1.json",
        "sg194_194_double_generic_final_result_v1.md",
        "sg194_194_generic_final_classification_summary_v1.json",
        "sg194_194_generic_final_classification_summary_v1.md",
    ],
    "generic_222_layer": [
        "sg194_222_og1601_identity_map_v1.json",
        "sg194_222_og1601_identity_map_v1.md",
        "sg194_ai_filter_bug_fix_v2.json",
        "sg194_ai_filter_bug_fix_v2.md",
        "sg194_dropped_ai_candidates_v3.json",
        "sg194_dropped_ai_candidates_v3.md",
        "sg194_native_ai_over_bs_quotient_fix_v2.json",
        "sg194_native_ai_over_bs_quotient_fix_v2.md",
        "sg194_222_single_generic_final_result_v1.json",
        "sg194_222_single_generic_final_result_v1.md",
        "sg194_222_double_generic_final_result_v1.json",
        "sg194_222_double_generic_final_result_v1.md",
        "sg194_222_generic_final_classification_summary_v1.json",
        "sg194_222_generic_final_classification_summary_v1.md",
    ],
    "oracle_compare_layer": [
        "sg194_222_generic_vs_topmat_oracle_v1.json",
        "sg194_222_generic_vs_topmat_oracle_v1.md",
        "sg194_topmat_oracle_from_copy_v1.json",
        "sg194_topmat_oracle_from_copy_v1.md",
        "sg194_topmat_copy_modification_log_v1.json",
        "sg194_topmat_copy_modification_log_v1.md",
    ],
    "semantics_layer": [
        "sg194_pipeline_consistency_checks_v8.json",
        "sg194_pipeline_consistency_checks_v8.md",
        "sg194_pipeline_status_semantics_v5.json",
        "sg194_pipeline_status_semantics_v5.md",
    ],
    "cleanup_layer": [
        "sg194_refactor_cleanup_v8.json",
        "sg194_refactor_cleanup_v8.md",
    ],
}


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    reset_dir(PACKAGE_DIR)
    for layer, names in COPY_LAYOUT.items():
        layer_dir = PACKAGE_DIR / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copy2(ROOT / name, layer_dir / name)

    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# Review Package: SG194 Backend-Free Generic v1",
                "",
                "- Scope: backend-free generic-path purity, 194 generic regression, 222 native generic probe, oracle compare, semantics, and cleanup.",
                "- 194 status in this package: backend-free raw current object is reproduced, but target-object extraction is still blocked.",
                "- 222 status in this package: native backend-free result is compare-only consistent with its own path, but still provisional because rejected AI candidates remain.",
                "- Oracle policy: copied topmat remains compare-only and never overwrites native final slots.",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "1. `purity_layer/sg194_generic_path_purity_audit_v1.json`",
                "2. `purity_layer/sg194_backend_dependency_cut_v1.json`",
                "3. `generality_layer/sg194_generality_verdict_v3.json`",
                "4. `generality_layer/sg194_case_by_case_map_v3.json`",
                "5. `generic_194_layer/sg194_194_generic_regression_v1.json`",
                "6. `generic_222_layer/sg194_222_generic_final_classification_summary_v1.json`",
                "7. `oracle_compare_layer/sg194_222_generic_vs_topmat_oracle_v1.json`",
                "8. `semantics_layer/sg194_pipeline_consistency_checks_v8.json`",
                "9. `semantics_layer/sg194_pipeline_status_semantics_v5.json`",
                "10. `cleanup_layer/sg194_refactor_cleanup_v8.json`",
            ]
        ),
    )

    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)

    if args.validate and not PACKAGE_TAR.exists():
        raise SystemExit("review package tarball missing")


if __name__ == "__main__":
    main()
