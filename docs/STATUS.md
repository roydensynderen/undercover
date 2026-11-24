# Status

The claims pilot from `docs/PLAN.md`, in progress.

## Built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is created and seeded from `data/` on first start. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_plans`, `get_policy_wording`, `get_instructions`, `list_handlers`, `list_steps` and `health`. Workflow operations: `start_claim`, `record_step`, `record_decision`, `pay_claim` and `sign_off`.
- The payment rule: an approval over the limit in `data/company.json` ($1,000) waits for sign-off, and `pay_claim` refuses it with 409 until a handler who can approve over the limit signs off. Signing off releases the payment.
- The agent's instructions are in `backend/instructions.md`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the hello-world page.

## Commands

- `npm run dev`: the backend on port 8000 and the dashboard on port 5173
- `uv run -m backend.seed`: reset the database to the data in `data/`
- `npm run check`: every check
