# SG194 topmat copied sources manifest v2

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Source policy

- source root: `/data/home/szhang/soft_sz/topmat_src`
- copied root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3`
- source root read-only in this round: `true`
- source tree modified: `false`

## Copied files

- source: `/data/home/szhang/soft_sz/topmat_src/topmat.py`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/original_sources/topmat.py`
  role: Read-only top-level CLI entrypoint for -mode 2 indicator evaluation.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/work_ind.sh`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/original_sources/work_ind.sh`
  role: Read-only shell wrapper that invokes dealfort.py and writes indout/inderr.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/dealfort.py`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/original_sources/dealfort.py`
  role: Read-only implementation of calc_ind() and dormant BR decomposition hooks.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/msginfo`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/msginfo`
  role: OG/BNS/type lookup table; contains OG 1494 <-> BNS 194.263 mapping.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/Lindex_194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/Lindex_194.263.txt`
  role: Indicator metadata/formula table for BNS 194.263.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/MsgAI_194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/MsgAI_194.263.txt`
  role: Magnetic AI generators in the 22-row magnetic-kirrep coordinate space.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/OrigAI_194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/OrigAI_194.263.txt`
  role: Ordinary/original AI generators; not the direct magnetic dAI object used here.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/basis_194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/basis_194.263.txt`
  role: Magnetic BS basis and invariant factors for BNS 194.263.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/mwyck-mag/194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/mwyck-mag/194.263.txt`
  role: Magnetic Wyckoff data used by topmat reference workflows.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/pairfiles_msghspk/194.263.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/pairfiles_msghspk/194.263.txt`
  role: Magnetic high-symmetry k-point pairing file for BNS 194.263.
  identical bytes after copy: `true`
- source: `/data/home/szhang/soft_sz/topmat_src/BilBaoData/mkpoints/194.txt`
  copied: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/mkpoints_194.txt`
  role: Reference k-point path data copied under a renamed local filename.
  identical bytes after copy: `true`

## Local modifications after copy

- `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/sg194_topmat_experimental_compute_v2.py`: Experimental benchmark driver that reads the copied reference files and writes JSON/MD deliverables; it does not modify the copied source snapshots.
