DOCS & TESTS POLICY — AARD

Purpose
-------
Define mandatory steps and canonical locations for documentation and tests when adding or modifying modules/services.

Documentation rules
-------------------
- Every new or changed service/module/component must have a sibling doc under:
  - `backend/docs/services/<service>.md`
  - `backend/docs/components/<component>.md`
  - `backend/docs/capabilities/<capability>.md`
  - `backend/docs/agents/<agent>.md`
- Doc template (strict):

```
## <EntityName>
Type:
Role:
Inputs:
Outputs:
Side-effects:
LLM usage: (yes/no; prompt_id/prompt_version if yes)
Events emitted:
Owner:
Readiness: PASS / FAIL (with reason)
```

- Docs must be added/updated in the same commit as code changes that affect behavior.
- If a change affects service contracts, CI (when enabled) must verify presence/updates of the service doc.

Tests policy
------------
- Tests must live next to the code they exercise or in mirrored `backend/tests/` structure:
  - Unit tests: `backend/app/<module>/tests/test_*.py` or `backend/tests/<module>/test_*.py`
  - Integration tests: `backend/tests/integration/`
- Naming & placement rule:
  - For `backend/app/services/foo.py`, unit tests should be `backend/app/services/test_foo.py` or `backend/tests/services/test_foo.py`
- Test scope rules:
  - Cursor/agents must run only tests relevant to the active block.
  - No global "run all" without explicit human approval.
- Test metadata:
  - Each test file must include a header comment listing block(s) it belongs to and required env flags.
- Prompt tests:
  - Canonical prompts must include unit/integration tests validating expected response patterns (store under `tests/prompts/` or adjacent to prompt files).

Process enforcement
------------------
- Documentation and tests are part of the "definition of done" for any change that affects contracts.
- On block completion, include test status and links to updated docs in BLOCK STATUS.

CI hooks (future)
-----------------
- When CI is enabled, enforce schema validation for ExecutionEvent and PromptAssignment in tests.


