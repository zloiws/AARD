# Decision Model — AARD

All meaningful system behavior is expressed as decisions.

A text response alone is not a decision.

## Decision structure

A decision must include:

- intent
  Normalized representation of human intent

- context
  Relevant memory and environment snapshot

- interpretation
  How the system understands the intent

- proposed_action
  What the system suggests or plans to do

- execution_trace
  What was actually executed (if any)

- outcome
  Result of execution

- confidence
  System confidence in interpretation and outcome

- feedback
  Human or system feedback

## Evaluation

Decisions are evaluated over time.
Improvement is measured by:
- reduction of misunderstandings
- faster convergence on correct intent
- reduced need for correction

The system does not optimize for correctness in isolation.
It optimizes for usefulness to the human.
