# Architecture Rules — AARD

AARD architecture exists to support human–AI interaction,
not to model intelligence.

The system is built around interpretation, not cognition.

## Core principles

1. No hidden logic
All system behavior must be explainable via:
- explicit state
- explicit configuration
- explicit examples

Implicit adaptation is forbidden.

2. Decisions are first-class objects
Architecture must revolve around decisions, not responses.

Every architectural component must either:
- interpret intent
- prepare a decision
- execute a decision
- observe and record a decision

3. No autonomous evolution
The system must not evolve without human visibility.
Any change in behavior must be:
- observable
- attributable
- reversible

4. Prefer composition over intelligence
Do not design "smart" components.
Design small, composable, replaceable components.

5. Configuration over code
Behavior changes should be achieved via:
- configuration
- prompt changes
- example sets

Not via new algorithms.

6. Failure is expected
Architecture must assume:
- misunderstanding
- partial execution
- incorrect assumptions

Failure handling is mandatory, not optional.
