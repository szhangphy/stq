# Second-Group Onboarding

- group: `10.4.1.31`
- trust policy: `symmetry_operations_only`
- primary blocker: `generic_current_row_compatibility_builder`

## Trusted Sources

- `common/P1_character.json`
- `common/L1_character.json`
- `common/P4_character.json`

## Sample Probe

- `P1` (point): k=`[0.0, 0.0, 0.0]`, ops=`16`, unitary/antiunitary=`8/8`
- `L1` (line): k=`[0.0, 0.2, 0.0]`, ops=`8`, unitary/antiunitary=`4/4`
- `P4` (point): k=`[0.0, 0.5, 0.0]`, ops=`16`, unitary/antiunitary=`8/8`

## Missing Generic Builders

- `generic_k_geometry_builder_from_symmetry_ops`
- `generic_current_row_compatibility_builder`
- `generic_local_ai_builder_from_site_symmetry_data`
- `generic_direct_quotient_builder_once_bs_ai_exist`
