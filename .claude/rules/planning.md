# Planning Step

## When to Invoke

Before writing any test for a new endpoint, model, or feature — every time, automatically.
This step produces a design artifact that tests are derived from. No test may be written before the design is approved.

---

## Phase 1 — Clarify Requirements

Review the feature request and identify anything that is ambiguous or unstated. Ask the user to resolve each unclear point before proceeding. Topics to probe:

- **Fields**: names, types (string, int, decimal, date, FK), required vs. optional, default values
- **Validation rules**: constraints, min/max, uniqueness, format (e.g. CNPJ), and what error message to return
- **Business semantics**: what does a term mean in domain context (e.g. "paid", "overdue", "partially paid")?
- **Edge cases**: what happens when a value is zero, negative, a duplicate, missing, or in an unexpected state?

Do not assume. If the request is clear enough to answer a question without asking, state the assumption explicitly and move on. Only ask when genuinely ambiguous.

---

## Phase 2 — Clarify Architecture

Always ask about these four decisions explicitly, even if the answer seems obvious:

1. **Service layer needed?**
   Ask whether the feature meets all three criteria from `architecture.md`:
   - Spans multiple models not naturally related through a single serializer `create()`
   - Involves stateful transitions
   - Must be reused from more than one call site
   If all three are true: a service is warranted. Otherwise: logic goes in the serializer.

2. **New model or existing?**
   Ask whether a new DB model (and migration) is required, or whether an existing model can be extended with new fields.

3. **Permission class**
   Ask which permission class applies:
   - `IsSuperUser` — create/update/delete on admin-owned resources
   - `IsAuthenticated` — read-only endpoints any authenticated user may access
   - `AllowAny` — login only; must be justified with an inline comment in the view

4. **New payment subtype?**
   Ask whether the feature introduces a new entry in the `TipoPagamento` discriminated union. If yes, the full 8-step checklist in `payments.md` applies.

---

## Phase 3 — Design Output

Write the design summary to a Claude plan file (`.claude/plans/`). Never commit this file to the repo.

The design summary must include:

### Endpoint Spec
- HTTP method and URL pattern (e.g. `POST /api/pagamento/implantacao/`)
- Permission class (with justification if `AllowAny`)
- Request body: each field with name, type, and required/optional
- Response: status code and response body shape

### Test Case List
List every test that will be written, using the naming convention `test_<action>_<condition>`. Always include the four mandatory cases from `testing.md`:
1. Unauthenticated → `401`
2. Authenticated, wrong permission → `403`
3. Happy path → `201` or `200`, DB state verified
4. Validation error → `400`, correct field name in `response.data`

Then list any additional edge-case tests identified in Phase 1.

### Architectural Decisions
Record the answer and rationale for each of the four Phase 2 questions.

### Resolved Clarifications
List every question asked in Phase 1 and the user's answer, so the reasoning is traceable.

---

## Phase 4 — Approval Gate

Present the design summary to the user and ask for explicit approval before starting TDD.
Only begin writing tests after the user confirms the design is correct.
If the user requests changes, update the design summary and ask again.
