# 222 AI Filter Bug Fix v2

- silent drop removed: `True`
- native final uses oracle override: `False`
- root cause: `The old fake-generic path silently reported final quotient data after rejecting AI candidates. The backend-free path now records every rejected or unembedded candidate explicitly and keeps native final verification provisional when rejections remain.`
- remaining blocker: `{'single_incompatible_family_letters': ['a', 'b', 'g'], 'double_incompatible_family_letters': ['a', 'b', 'g'], 'note': 'The silent-drop bug is fixed, but the native backend-free path still rejects a/b/g-family AI candidates on the current compatibility matrix, so the native final object remains provisional.'}`
- single: `11/10/Z x Z4` status=`failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient`
- double: `11/10/Z x Z4` status=`failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient`
