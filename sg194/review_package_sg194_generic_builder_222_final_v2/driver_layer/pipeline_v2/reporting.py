from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import GroupSpec
from .utils import repo_rel, tar_directory, write_json, write_text


def _md_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _format_value(value: Any) -> str:
    return "null" if value is None else str(value)


def write_pipeline_outputs(
    output_dir: Path,
    repo_root: Path,
    spec: GroupSpec,
    geometry: dict[str, Any],
    alignment: dict[str, Any],
    bs_summary: dict[str, Any],
    ai_summary: dict[str, Any],
    quotient_summary: dict[str, Any],
    final_status: dict[str, Any],
    checks: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "geometry": output_dir / "geometry_summary.json",
        "alignment": output_dir / "representation_alignment_summary.json",
        "bs": output_dir / "bs_results.json",
        "ai": output_dir / "ai_results.json",
        "quotient": output_dir / "quotient_results.json",
        "final_status": output_dir / "final_status_summary.json",
        "checks": output_dir / "consistency_checks.json",
    }
    write_json(files["geometry"], geometry)
    write_json(files["alignment"], alignment)
    write_json(files["bs"], bs_summary)
    write_json(files["ai"], ai_summary)
    write_json(files["quotient"], quotient_summary)
    write_json(files["final_status"], final_status)
    write_json(files["checks"], checks)

    md_files = {
        "geometry": output_dir / "geometry_summary.md",
        "alignment": output_dir / "representation_alignment_summary.md",
        "bs": output_dir / "bs_results.md",
        "ai": output_dir / "ai_results.md",
        "quotient": output_dir / "quotient_results.md",
        "final_status": output_dir / "final_status_summary.md",
        "checks": output_dir / "consistency_checks.md",
    }
    write_text(
        md_files["geometry"],
        "\n".join(
            [
                "# Geometry Summary",
                "",
                *(
                    _md_list(
                        [
                            f"group: `{spec.group_id}`",
                            f"status: `{geometry.get('status', 'available')}`",
                            f"shared backbone: `{geometry.get('shared_backbone_available')}`",
                            f"object counts: `{geometry.get('object_counts')}`",
                            f"compatibility matrix shape: `{geometry.get('compatibility_matrix_shape')}`",
                        ]
                    )
                ),
            ]
        ),
    )
    write_text(
        md_files["alignment"],
        "\n".join(
            [
                "# Representation Alignment Summary",
                "",
                *(
                    _md_list(
                        [
                            f"single target exact alignment: `{alignment.get('single', {}).get('target', {}).get('exact_alignment_status')}`",
                            f"double target exact alignment: `{alignment.get('double', {}).get('target', {}).get('exact_alignment_status')}`",
                            f"single target row language: `{alignment.get('single', {}).get('target', {}).get('row_language_kind')}`",
                            f"double target row language: `{alignment.get('double', {}).get('target', {}).get('row_language_kind')}`",
                        ]
                    )
                ),
            ]
        ),
    )
    for key, title, field in [
        ("bs", "BS Results", "dBS"),
        ("ai", "AI Results", "dAI"),
    ]:
        write_text(
            md_files[key],
            "\n".join(
                [
                    f"# {title}",
                    "",
                    *(
                        _md_list(
                            [
                                (
                                    f"{item['object_id']}: `{_format_value(item[field])}` in "
                                    f"`{item['row_language_level']}` / `{item['object_kind']}` / "
                                    f"`{item['availability']}`"
                                    + (f" blocker=`{item['blocker']}`" if item.get("blocker") else "")
                                )
                                for item in (bs_summary if key == "bs" else ai_summary)["objects"]
                            ]
                        )
                    ),
                ]
            ),
        )
    write_text(
        md_files["quotient"],
        "\n".join(
            [
                "# Quotient Results",
                "",
                *(
                    _md_list(
                        [
                            (
                                f"{item['object_id']}: `{_format_value(item['classification'])}` via "
                                f"`{item['quotient_derivation_mode']}` / `{item['availability']}`"
                                + (f" blocker=`{item['blocker']}`" if item.get("blocker") else "")
                            )
                            for item in quotient_summary["objects"]
                        ]
                    )
                ),
            ]
        ),
    )
    write_text(
        md_files["final_status"],
        "\n".join(
            [
                "# Final Status Summary",
                "",
                *(
                    _md_list(
                        [
                            (
                                f"single final object: `{final_status['single_final']['object_kind']}` -> "
                                f"`{_format_value(final_status['single_final']['dBS'])}/"
                                f"{_format_value(final_status['single_final']['dAI'])}/"
                                f"{_format_value(final_status['single_final']['classification'])}`"
                            ),
                            (
                                f"double final object: `{final_status['double_final']['object_kind']}` -> "
                                f"`{_format_value(final_status['double_final']['dBS'])}/"
                                f"{_format_value(final_status['double_final']['dAI'])}/"
                                f"{_format_value(final_status['double_final']['classification'])}`"
                            ),
                            f"same final object: `{final_status.get('same_final_object')}`",
                            *(["relation: `" + final_status["relation"] + "`"] if "relation" in final_status else []),
                            *(["status: `" + final_status["status"] + "`"] if "status" in final_status else []),
                            *(["note: `" + final_status["note"] + "`"] if "note" in final_status else []),
                        ]
                    )
                ),
            ]
        ),
    )
    write_text(
        md_files["checks"],
        "\n".join(
            [
                "# Consistency Checks",
                "",
                *(_md_list([f"{item['name']}: `{item['passed']}`" for item in checks["checks"]])),
                "",
                f"- checks passed: `{checks['checks_passed']}`",
                f"- final results available: `{checks['final_results_available']}`",
                f"- final results verified: `{checks['final_results_verified']}`",
                f"- legacy all passed: `{checks['all_passed']}`",
            ]
        ),
    )

    manifest = {
        "group": spec.group_id,
        "spec_key": spec.key,
        "output_dir": repo_rel(output_dir, repo_root),
        "files": {key: repo_rel(path, repo_root) for key, path in {**files, **md_files}.items()},
    }
    manifest_path = output_dir / "package_manifest.json"
    write_json(manifest_path, manifest)
    manifest["package_manifest"] = repo_rel(manifest_path, repo_root)
    return manifest


def finalize_output_package(output_dir: Path, repo_root: Path) -> str:
    tarball = output_dir.with_suffix(".tar.gz")
    tar_directory(output_dir, tarball)
    return repo_rel(tarball, repo_root)
