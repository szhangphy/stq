# SG194 topmat read-only audit v3

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Read-only audit scope

- `/data/home/szhang/soft_sz/topmat_src/topmat.py`
- `/data/home/szhang/soft_sz/topmat_src/work_ind.sh`
- `/data/home/szhang/soft_sz/topmat_src/dealfort.py`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/msginfo`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/Lindex_194.263.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/MsgAI_194.263.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/OrigAI_194.263.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/output/basis_194.263.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/mwyck-mag/194.263.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/mkpoints/194.txt`
- `/data/home/szhang/soft_sz/topmat_src/BilBaoData/pairfiles_msghspk/194.263.txt`

## What topmat_src directly does

- direct CLI indicator evaluation available: `true`
- direct CLI full classification available: `false`
- classification recoverable from reference data files: `true`
- direct dBS scalar output available: `false`
- direct dAI scalar output available: `false`

## Direct read-only run

- success: `true`
- working directory: `/tmp/sg194_topmat_ro_test_4jc1ehga`
- command: `python3 /data/home/szhang/soft_sz/topmat_src/topmat.py -og 1494 -sg 194 -mode 2`
- indout: `Z6=0,`

## Read-only limitation

- `dealfort.py::read_SiteK()` expects `BilBaoData/BRlist2_A/SiteK_<sg>.cht`.
- `BilBaoData/BRlist2_A` is absent in this source tree, so the dormant BR decomposition path is unavailable here.
