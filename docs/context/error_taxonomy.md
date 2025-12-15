# Error Taxonomy — AARD

Errors are a normal part of interaction.
They must be classified, not hidden.

## Error types

1. Interpretation Error
Human intent was misunderstood.

2. Reasoning Error
The system produced an incorrect plan or conclusion.

3. Tool Error
A tool failed, misbehaved, or was misused.

4. Data Error
The system used incorrect, outdated, or incomplete data.

5. Environment Error
External systems failed or behaved unexpectedly.

6. Human Override
The human corrected or rejected system behavior.

## Rules

- Errors must not be treated uniformly.
- Each error type requires different mitigation.
- Errors are not "learning signals" by default.

Error handling must:
- preserve traceability
- avoid overcorrection
- remain reversible

Reducing error impact is more important
than eliminating errors entirely.
