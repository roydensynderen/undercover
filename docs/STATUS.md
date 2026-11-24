# Status

The claims pilot from `docs/PLAN.md`, in progress.

## Built

- `backend/`: FastAPI on SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is created and seeded from `data/` on first start. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_plans`, `get_policy_wording`, `list_handlers`, and `health`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the hello-world page.

## Commands

- `npm run dev`: the backend on port 8000 and the dashboard on port 5173
- `uv run -m backend.seed`: reset the database to the data in `data/`
- `npm run check`: every check
