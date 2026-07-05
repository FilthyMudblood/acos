# Known Issues and Pitfalls

Track recurring issues with reproducible details and proven mitigations.

## Issue Template
- ID: BUG-YYYYMMDD-XX
- Area:
- Symptom:
- Reproduction:
- Root cause:
- Mitigation:
- Permanent fix status: pending | in-progress | fixed
- Regression test/check:

---

## Example
- ID: BUG-20260425-01
- Area: Frontend terminal session rendering
- Symptom: Output panel appears stale after rapid command updates.
- Reproduction: Trigger multiple updates within short intervals in Streamlit UI.
- Root cause: UI rerender timing race with state update batching.
- Mitigation: Force refresh after batched state write in terminal update flow.
- Permanent fix status: pending
- Regression test/check: Run rapid update scenario and confirm panel reflects latest state.
