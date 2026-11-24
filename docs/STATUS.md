# Status

The claims pilot from `docs/PLAN.md` is built: the backend, the UnderCover Agent and the dashboard.

## Built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is created and seeded from `data/` on first start; `data/evals/` is never read.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (earlier claims only, no personal details), `get_plans`, `get_policy_wording`, `get_instructions`, `list_handlers`, `list_steps` and `health`.
  - Workflow operations: `start_claim`, `record_step`, `record_decision`, `pay_claim` and `sign_off`.
  - Claim states: `waiting`, `in_progress`, `awaiting_sign_off` and `decided`.
  - The payment rule: an approval over the limit in `data/company.json` ($1,000) waits for sign-off, and `pay_claim` refuses it with 409 until a handler who can approve over the limit signs off. Signing off releases the payment. Payments are records only.
  - The agent's instructions are in `backend/instructions.md`.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` on OpenRouter (`openai/gpt-6-luna` at low reasoning effort, or `MODEL_NAME`). Its tools wrap the backend's read operations, `record_decision` and `pay_claim`, and it fetches its instructions from `get_instructions`. `run(claim_id, thread_id)` marks the claim in progress and records each tool call, tool result and reply as a step.
- `dashboard/`: React, in UnderCover's brand with light and dark modes.
  - The queue (`#/`) lists every claim with its state, decision and payout, and counts the claims in each state.
  - The claim page (`#/claims/CLM-1001`) shows the story, items, documents, policy, claim history, the agent's decision with its reason, policy section, payout and payment, and the agent's steps as they arrive. For a claim waiting for sign-off, a handler who can approve over the limit signs off there and releases the payment.
  - The instructions page (`#/instructions`) shows the agent's instructions, read only.
  - Pages refresh every two seconds until the agent has finished.
- `e2e/`: Playwright tests of the queue, a claim, the steps, sign-off and the instructions. They run their own backend (port 8001, database `e2e/e2e.db`, reseeded each run) and dashboard (port 5174).

## Commands

- `npm run dev`: the backend on port 8000 and the dashboard on http://localhost:5173
- `uv run -m agent`: work every waiting claim in queue order (the backend must be running)
- `uv run -m agent CLM-1001`: work one claim
  - A run that stops part way (for example on OpenRouter's rate limit for new accounts, 20 requests a minute) leaves that claim in progress. `uv run -m agent` skips it, so run it by id. The model client retries rate limits with backoff.
- `uv run -m backend.seed`: reset the database to the data in `data/`
- `npm run check`: every check

## Not built

As the spec says: no claims manual, no sign-in, no real payments and no messages to customers. The agent is not yet scored against the handlers' decisions in `data/evals/`.
