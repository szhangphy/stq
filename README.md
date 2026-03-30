# stq

This repository curates the reusable STQ code from the original `comprel` workspace and splits it into two audit-friendly branches.

## Project Summary

- `main` keeps the reusable infrastructure: Wyckoff tooling, single/double-group workflow scripts, common matrices and summaries, vendored `SSGReps`, and the independent raw-matrix recompute helper.
- `sg194-special` is derived from `main` and adds the SG194-specific audit, patch, lift, portability, alignment, mismatch-localization, and external-matrix workflow layer.

## Branch Guide

- `main`: reusable code and data only.
- `sg194-special`: `main` plus the SG194-specific workspace.

## Main Branch Layout

- `common/`: reusable scripts, shared matrices, audit summaries, prompts, and handoff notes.
- `common/SSGReps/`: vendored `SSGReps` sources plus packaged data assets.
- `common/independent_recompute_minipack/`: raw snapshots and an independent recompute helper.

## SG194 Layer

The `sg194-special` branch depends on the reusable modules in `main`, especially:

- `common/swyckoff_k.py`
- `common/swyckoff_r.py`
- `common/SSGReps.py`
- `common/rep_utils.py`
- `common/SG_utils.py`
- `common/debug_single_group_ai_bridge.py`
- `common/debug_single_group_ai_expanded.py`

## Key Entry Points On `main`

- `common/debug_single_group_ai_bridge.py`
- `common/debug_single_group_ai_expanded.py`
- `common/debug_double_group_feasibility_10.4.1.31.py`
- `common/debug_double_group_kspace_backbone_10.4.1.31.py`
- `common/debug_double_group_pointlike_coreps_10.4.1.31.py`
- `common/independent_recompute_minipack/recompute_from_raw.py`

## Basic Usage

1. Extract the packaged `SSGReps` lookup database:

   ```bash
   tar -xzf common/SSGReps/ssg_data/identify.pkl.tar.gz -C common/SSGReps/ssg_data
   ```

2. Run a reusable workflow from the repo root or from inside `common/`:

   ```bash
   cd common
   python3 debug_double_group_feasibility_10.4.1.31.py
   ```

   or

   ```bash
   PYTHONPATH=common python3 common/debug_single_group_ai_bridge.py
   ```

3. On `sg194-special`, run SG194 workflows with `common/` on `PYTHONPATH` so the SG194 scripts can reuse the shared modules from `main`.

## Known Limits

- The original workspace did not contain a pinned environment file such as `requirements.txt` or `pyproject.toml`.
- Observed third-party Python dependencies from the checked-in sources include `numpy`, `sympy`, and `spglib`.
- `common/SSGReps/ssg_data/identify.pkl` is intentionally stored as `identify.pkl.tar.gz` to avoid checking in the unpacked large binary.
- Many JSON, Markdown, and TeX files are audit artifacts and intermediate matrix snapshots rather than a polished package API.
