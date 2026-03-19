---
description: "Planning step before any TDD cycle — clarify requirements and produce a design"
---

# Plan Feature

Use this prompt before writing any test for a new endpoint, model, or feature.
This step produces a design artifact that tests are derived from.
Do not write any test before the design is approved by the user.

## Phase 1 — Clarify Requirements

Review the feature request. Ask the user about anything ambiguous:

- **Fields**: names, types (string, int, decimal, date, FK), required vs. optional, default values
- **Validation rules**: constraints, min/max, uniqueness, format (e.g. CNPJ), error messages
- **Business semantics**: what do domain terms mean? (e.g. "paid", "overdue", "partially paid")
- **Edge cases**: what happens when a value is zero, negative, a duplicate, or missing?

Only ask when genuinely ambiguous. State assumptions explicitly and move on if the answer is clear.

## Phase 2 — Clarify Architecture

Ask explicitly about these four decisions:

1. **Service layer needed?** Does the feature meet all three criteria?
   - Spans multiple models not naturally related through a single serializer `create()`
   - Involves stateful transitions
   - Must be reused from more than one call site

2. **New model or existing?** New DB model + migration, or extend an existing model?

3. **Permission class?** `IsSuperUser` / `IsAuthenticated` / `AllowAny` (login only)?

4. **New payment subtype?** If yes, the full 8-step checklist in `.github/prompts/new-payment-type.prompt.md` applies.

## Phase 3 — Design Output

Write a design summary that includes:

### Endpoint Spec
- HTTP method and URL (e.g. `POST /api/pagamento/implantacao/`)
- Permission class (with justification if `AllowAny`)
- Request body: each field with name, type, required/optional
- Response: status code and body shape

### Test Case List
List every test using `test_<action>_<condition>` naming. Always include:
1. Unauthenticated → 401
2. Authenticated, wrong permission → 403
3. Happy path → 201/200, DB state verified
4. Validation error → 400, correct field name in response

Plus any additional edge-case tests identified in Phase 1.

### Architectural Decisions
Record the answer and rationale for each Phase 2 question.

## Phase 4 — Approval Gate

Present the design summary to the user. Wait for explicit approval.
Only begin writing tests after confirmation.
If the user requests changes, update the design and ask again.
