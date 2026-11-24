# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds the claims queue, the UnderCover Agent that works it, and a dashboard where the handlers watch it and sign off large payouts. It follows `docs/TECH_STACK.md`, `docs/CODE_STANDARDS.md` and `docs/BRAND.md`, and builds on the hello-world skeleton in `docs/STATUS.md`.

## Approach

**The backend owns the rules.** Every rule the business cares about lives in the backend, not in the agent's prompt. The $1,000 sign-off rule in particular is enforced by `pay_claim`, so it holds even if the agent tries to pay. The agent can be wrong, but it can't break the rules.

**The agent only talks to the API.** It reads claims, policies, claim history, the policy wording and its own instructions through backend operations, wrapped as tools. Its instructions live in the backend so the dashboard can show exactly what the agent reads.

**The answer key stays out.** The backend seeds only from the files `data/README.md` lists as the insurer's systems. Nothing in `backend/` or `agent/` reads `data/evals/`, and a test checks that.

**Steps are recorded as the agent works.** The entry point streams the agent's updates and posts each tool call and each model reply to the backend as a step. The dashboard polls a claim while it's in progress, so the handlers see the steps arrive. This uses LangChain's streaming rather than middleware, which comes in the harness build.

**SQLite, kept simple.** One file database, `backend/undercover.db` (git-ignored), created and seeded from `data/` on first start. Reference records (policies, customers, plans) are stored as JSON columns since the pilot only reads them whole. Tests and the end-to-end run each use their own database file, set with the environment variable `UNDERCOVER_DB`.

### Claim states

The queue shows the four states the spec asks for. The seed data's `open` becomes `waiting`.

| State | Meaning | Set by |
|---|---|---|
| `waiting` | In the queue, not started | Seed |
| `in_progress` | The agent is working it | `start_claim` |
| `awaiting_sign_off` | Approved with a payout over $1,000; payment blocked | `record_decision` |
| `decided` | Approved, declined or referred, with nothing left to wait for | `record_decision` or `sign_off` |

A referral counts as decided: the agent's work is done and the claim goes to a handler.

### API operations

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Operation | Method and path | Used by |
|---|---|---|
| `health` | `GET /api/health` | Dashboard |
| `list_claims` | `GET /api/claims` | Dashboard, agent CLI |
| `get_claim` | `GET /api/claims/{claim_id}` | Agent, dashboard |
| `get_policy` | `GET /api/policies/{policy_id}` | Agent, dashboard |
| `get_claim_history` | `GET /api/customers/{customer_id}/claims` | Agent, dashboard |
| `get_plans` | `GET /api/plans` | Agent |
| `get_policy_wording` | `GET /api/policy-wording` | Agent |
| `get_instructions` | `GET /api/instructions` | Agent, dashboard |
| `list_handlers` | `GET /api/handlers` | Dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` | Agent entry point |
| `record_step` | `POST /api/claims/{claim_id}/steps` | Agent entry point |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | Dashboard |
| `record_decision` | `POST /api/claims/{claim_id}/decision` | Agent |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | Agent |
| `sign_off` | `POST /api/claims/{claim_id}/sign-off` | Dashboard |

`get_claim_history` returns only the earlier claims, not the customer's contact details, since the agent doesn't need personal data to decide a claim.

`record_decision` takes `decision` (`approve`, `decline` or `refer`), `payout` (0 unless approving), `reason` (two or three sentences) and `policy_section` (such as "3. Trip Delay"). `pay_claim` takes `amount`, which must match the approved payout. It returns 409 Conflict unless the claim is approved and either within the limit or signed off. `sign_off` takes a `handler_id`, which must belong to a handler who `can_approve_over_limit`; it records the sign-off and releases the payment. No real money moves: a payment is a row in the database.

The limit is read from `company.json` (`payout_approval_limit`), not hard-coded.

## Phase 1: Backend data and read operations

Build the database, the seeding and the read operations.

- `backend/db.py`: SQLite connection from `UNDERCOVER_DB` (default `backend/undercover.db`), the schema, and seeding from `data/` when the database is empty.
- `backend/seed.py`: `uv run -m backend.seed` wipes and reseeds the database.
- `backend/main.py`: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_plans`, `get_policy_wording`, `list_handlers`, with Pydantic response models. 404 for unknown ids.
- A pytest fixture that points `UNDERCOVER_DB` at a temporary file.

Success criteria:

- [x] `uv run pytest -q backend` passes, with tests for every operation, including 404s
- [x] A test asserts that no file in `backend/` or `agent/` mentions `data/evals` or `evals/`
- [x] `uv run -m backend.seed` creates the database; `GET /api/claims` returns 25 claims, all `waiting`, in queue order starting at `CLM-1001`
- [x] `GET /api/claims/CLM-1001` returns the story, items, documents and `amount_claimed` 420.00
- [x] `GET /api/customers/CUS-3001/claims` returns `CLM-0412` and no email or phone
- [x] `GET /api/policy-wording` returns the full policy wording, version 2026.1
- [x] Every route in `/openapi.json` has an `operationId` and a summary, and no optional parameters (checked by a test)
- [x] `npm run check:python` passes with coverage at or above 80%

## Phase 2: Backend workflow and the payment rule

Build the operations that move a claim through its states, and the rule that blocks large payments.

- `start_claim`, `record_step`, `record_decision`, `pay_claim`, `sign_off`, `get_instructions`.
- `backend/instructions.md`: the agent's instructions. Work the claim from its own records and the policy wording, check dates, waiting periods, limits, per-item limits, the deductible and exclusions, show the payout calculation, then record one decision with the section that settles it, and pay only if approved.
- `get_claim` includes the decision, payment and sign-off. The steps have their own operation, `list_steps`, so the agent's `get_claim` doesn't fill up with its own steps.

Success criteria:

- [x] Tests cover each state change: `waiting` → `in_progress` → `decided`, and `in_progress` → `awaiting_sign_off` → `decided`
- [x] An approval of $420.00 is `decided`, and `pay_claim` with 420.00 records the payment
- [x] An approval of $1,250.00 is `awaiting_sign_off`, and `pay_claim` returns 409 with a message that a handler must sign off
- [x] `sign_off` by a handler without `can_approve_over_limit` returns 403; by one with it, the claim becomes `decided` and the payment is recorded
- [x] `pay_claim` returns 409 for a declined or referred claim, a wrong amount, or a second payment
- [x] `record_decision` rejects a payout on a decline or refer, and an unknown decision value (422)
- [x] `GET /api/instructions` returns the text of `backend/instructions.md`
- [x] With the server running, the same sequence works with `curl` against `localhost:8000`
- [x] `npm run check:python` passes

## Phase 3: The UnderCover Agent

Replace the hello-world agent with the claims agent.

- `agent/main.py`: tools that wrap `get_claim`, `get_policy`, `get_claim_history`, `get_plans`, `get_policy_wording`, `record_decision` and `pay_claim`. `run(claim_id, thread_id)` fetches its instructions from `get_instructions`, calls `start_claim`, streams the agent and posts each tool call and reply with `record_step`, and returns the final reply. The model choice stays as it is: `openai/gpt-6-luna` at low reasoning effort, or `MODEL_NAME`.
- `agent/__main__.py`: `uv run -m agent` works every `waiting` claim in queue order; `uv run -m agent CLM-1001` works one claim. Each run gets a fresh thread id. It prints each claim's decision and payout.
- Tests use a stub model with scripted tool calls against a `TestClient` backend.

Success criteria:

- [x] A stub-model test runs a claim end to end: the tools are called, steps are recorded, the decision is saved and the payment is made
- [x] A stub-model test where the agent approves $1,250.00 and then calls `pay_claim` gets the 409 back as a tool result, and the claim stays `awaiting_sign_off` with no payment
- [x] A test checks the CLI picks only `waiting` claims, in queue order, and that a claim id argument runs just that claim
- [x] With `OPENROUTER_API_KEY` set and the backend running, `uv run -m agent CLM-1001` records a decision with a reason, a policy section and a payout, and `GET /api/claims/CLM-1001` shows its steps (this one call uses the real model; it costs a few cents, or nothing with `MODEL_NAME=openrouter/free`)
- [x] `npm run check:python` passes

## Phase 4: Dashboard queue and claim pages

Build the handlers' screens, with the brand.

- A small hash router (`#/`, `#/claims/CLM-1001`, `#/instructions`) so there's no new dependency.
- An API module with typed responses for each operation used.
- **Queue page**: each claim's id, type, customer story summary, amount claimed, state and payout, with a count per state. States use Sea Green, Marigold, Coral and Cerulean.
- **Claim page**: the story, items, documents, the policy and the claim history, and the decision with its reason, policy section and payout.
- Instrument Sans, Instrument Serif and JetBrains Mono from Google Fonts; brand colors as CSS variables; light and dark mode from the system setting. Amounts formatted as $1,250.00.

Success criteria:

- [ ] Vitest tests cover each page with a stubbed `fetch`, including an empty decision and a decided claim
- [ ] In the browser (Playwright MCP), the queue lists 25 claims and the state counts add up to 25
- [ ] Clicking a claim opens its page with its story, items, documents and policy
- [ ] After the Phase 3 run, CLM-1001's page shows the decision, reason, policy section and payout
- [ ] Both light and dark mode match `docs/BRAND.md`: rounded panels, no one-edge borders, no thin top lines
- [ ] `npm run check:ts` passes with coverage at or above 80%

## Phase 5: Agent steps, sign-off and instructions

Build the live view of the agent's work and the handler's part in the payment rule.

- **Steps on the claim page**: each step in order, with time and type (tool call, tool result, reply). While the claim is `in_progress` the page polls `get_claim` every two seconds and stops once it's done.
- **Sign-off**: on an `awaiting_sign_off` claim, a panel shows the payout and a choice of the handlers who can sign off, and a button to sign off. The payment shows once it's released.
- **Instructions page**: the agent's instructions from `get_instructions`, read only.

Success criteria:

- [ ] Vitest tests cover polling (it starts and stops), sign-off (success and a 403 error shown to the user) and the instructions page
- [ ] In the browser, running `uv run -m agent CLM-1002` while CLM-1002's page is open shows the steps arriving and then the decision
- [ ] In the browser, a claim the agent approved over $1,000 shows the sign-off panel with only the handlers who can approve over the limit; signing off moves it to `decided` and shows the payment
- [ ] The instructions page shows the same text as `backend/instructions.md`, with no way to edit it
- [ ] `npm run check:ts` passes

## Phase 6: End-to-end tests, the full queue and status

Tie it together and check the whole flow.

- Playwright starts the backend on its own database (`UNDERCOVER_DB` in the `webServer` `env`, reseeded at start), so tests don't touch the dev data.
- E2E tests seed decisions through the API (no model call): the queue, a decided claim, the sign-off flow, and the instructions page. The health test is updated or replaced.
- Run the agent on the whole queue once with the real model, as a smoke test, and look at the results by eye.
- `docs/STATUS.md`: what's built, how to run it (`npm run dev`, `uv run -m agent`, `uv run -m agent CLM-1001`, `uv run -m backend.seed`), and what's left out per the spec.

Success criteria:

- [ ] `npm run e2e` passes: queue, claim page, sign-off moving a claim to `decided`, and instructions
- [ ] `uv run -m backend.seed` then `uv run -m agent` works all 25 claims; every claim ends `decided` or `awaiting_sign_off`, and none over $1,000 has a payment before sign-off
- [ ] `docs/STATUS.md` lists every command above and they all work from a fresh clone after `uv sync` and `npm install`
- [ ] `npm run check` passes in full

## Not in this build

As the spec says: no claims manual, no sign-in, no real payments and no messages to customers. Scoring the agent against the handlers' decisions in `data/evals/` comes with the evaluations in a later build; this build only makes sure the agent can't see them.
