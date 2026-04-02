# Stage2 Role Cleanup

- stage2 was rewritten to consumer-only mode, but the authoritative runtime probe still fails before stage2 can consume a full result.
- failure: mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character: Linear system has no solution
