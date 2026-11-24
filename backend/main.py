"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Decision,
    DecisionIn,
    Handler,
    Payment,
    PaymentIn,
    Plans,
    Policy,
    PreviousClaim,
    SignOff,
    SignOffIn,
    Step,
    StepIn,
    Text,
)

INSTRUCTIONS = Path(__file__).resolve().parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)
Db = Annotated[sqlite3.Connection, Depends(db.database)]


def now() -> str:
    """Return the time now in UTC, as ISO 8601."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def approval_limit(conn: sqlite3.Connection) -> float:
    """Return the payout above which a handler must sign off."""
    return db.setting(conn, "company")["payout_approval_limit"]


def found[T](value: T | None, what: str) -> T:
    """Return the value, or raise a 404 naming what was missing."""
    if value is None:
        raise HTTPException(404, f"{what} not found")
    return value


def claim_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    """Return the claim's row, or raise a 404."""
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    return found(row, f"Claim {claim_id}")


def one(conn: sqlite3.Connection, table: str, claim_id: str) -> dict[str, Any] | None:
    """Return a claim's row from a table, such as its decision, as a dict."""
    row = conn.execute(
        f"SELECT * FROM {table} WHERE claim_id = ?",  # noqa: S608
        (claim_id,),
    ).fetchone()
    return dict(row) if row else None


def load_claim(conn: sqlite3.Connection, claim_id: str) -> Claim:
    """Assemble a claim with its decision, sign-off and payment."""
    row = claim_row(conn, claim_id)
    body = json.loads(row["body"])
    customer = db.record(conn, "customer", body["customer_id"]) or {}
    decision = one(conn, "decisions", claim_id)
    sign_off = one(conn, "sign_offs", claim_id)
    payment = one(conn, "payments", claim_id)
    if sign_off:
        handler = db.record(conn, "handler", sign_off["handler_id"]) or {}
        sign_off["handler_name"] = handler.get("name", "")
    return Claim(
        **body,
        customer_name=customer.get("name", ""),
        status=row["status"],
        decision=Decision(**decision) if decision else None,
        sign_off=SignOff(**sign_off) if sign_off else None,
        payment=Payment(**payment) if payment else None,
    )


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: Db) -> list[ClaimSummary]:
    """List the claims queue in order, with where each claim stands."""
    names = {c["customer_id"]: c["name"] for c in db.records(conn, "customer")}
    rows = conn.execute(
        "SELECT c.status, c.body, d.decision, d.payout FROM claims c "
        "LEFT JOIN decisions d USING (claim_id) ORDER BY c.position"
    ).fetchall()
    summaries = []
    for row in rows:
        body = json.loads(row["body"])
        summaries.append(
            ClaimSummary(
                claim_id=body["claim_id"],
                claim_type=body["claim_type"],
                summary=body["summary"],
                customer_name=names.get(body["customer_id"], ""),
                submitted_on=body["submitted_on"],
                amount_claimed=body["amount_claimed"],
                status=row["status"],
                decision=row["decision"],
                payout=row["payout"],
            )
        )
    return summaries


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: Db) -> Claim:
    """Get one claim in full, with its decision, sign-off and payment."""
    return load_claim(conn, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: Db) -> Policy:
    """Get a customer's policy: the plan, add-ons, trip and travelers."""
    return Policy(**found(db.record(conn, "policy", policy_id), f"Policy {policy_id}"))


@app.get("/api/customers/{customer_id}/claims", operation_id="get_claim_history")
def get_claim_history(customer_id: str, conn: Db) -> list[PreviousClaim]:
    """Get a customer's earlier claims, without their personal details."""
    customer = found(
        db.record(conn, "customer", customer_id), f"Customer {customer_id}"
    )
    return [PreviousClaim(**claim) for claim in customer["previous_claims"]]


@app.get("/api/plans", operation_id="get_plans")
def get_plans(conn: Db) -> Plans:
    """Get the three plans' limits and deductibles, and the add-ons."""
    return Plans.model_validate(db.setting(conn, "plans"))


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording, the contract with the customer."""
    return Text(text=(db.DATA / "policy_wording.md").read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: Db) -> list[Handler]:
    """List the claims handlers and whether each can sign off large payouts."""
    return [Handler(**handler) for handler in db.records(conn, "handler")]


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the UnderCover Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text(encoding="utf-8"))


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, conn: Db) -> Claim:
    """Mark a waiting claim as in progress, as the agent starts on it."""
    row = claim_row(conn, claim_id)
    if row["status"] not in ("waiting", "in_progress"):
        raise HTTPException(409, f"Claim {claim_id} has already been decided")
    conn.execute(
        "UPDATE claims SET status = 'in_progress' WHERE claim_id = ?", (claim_id,)
    )
    return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="record_step")
def record_step(claim_id: str, step: StepIn, conn: Db) -> Step:
    """Record one step of the agent's work on a claim."""
    claim_row(conn, claim_id)
    at = now()
    cursor = conn.execute(
        "INSERT INTO steps (claim_id, kind, text, at) VALUES (?, ?, ?, ?)",
        (claim_id, step.kind, step.text, at),
    )
    return Step(step_id=cursor.lastrowid or 0, kind=step.kind, text=step.text, at=at)


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, conn: Db) -> list[Step]:
    """List the steps of the agent's work on a claim, in order."""
    claim_row(conn, claim_id)
    rows = conn.execute(
        "SELECT step_id, kind, text, at FROM steps WHERE claim_id = ? ORDER BY step_id",
        (claim_id,),
    ).fetchall()
    return [Step(**dict(row)) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: DecisionIn, conn: Db) -> Claim:
    """Approve, decline or refer a claim; a large payout waits for sign-off."""
    if claim_row(conn, claim_id)["status"] != "in_progress":
        raise HTTPException(409, f"Claim {claim_id} is not in progress")
    if decision.decision != "approve" and decision.payout != 0:
        raise HTTPException(422, "Only an approval can have a payout")
    over_limit = decision.decision == "approve" and decision.payout > approval_limit(
        conn
    )
    conn.execute(
        "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
        (
            claim_id,
            decision.decision,
            round(decision.payout, 2),
            decision.reason,
            decision.policy_section,
            now(),
        ),
    )
    conn.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ?",
        ("awaiting_sign_off" if over_limit else "decided", claim_id),
    )
    return load_claim(conn, claim_id)


def insert_payment(conn: sqlite3.Connection, claim_id: str, amount: float) -> None:
    """Record a payment; no real money moves in the pilot."""
    conn.execute("INSERT INTO payments VALUES (?, ?, ?)", (claim_id, amount, now()))


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentIn, conn: Db) -> Claim:
    """Pay an approved claim; a payout over the limit needs a sign-off first."""
    claim = load_claim(conn, claim_id)
    if claim.decision is None or claim.decision.decision != "approve":
        raise HTTPException(409, f"Claim {claim_id} has not been approved")
    if claim.payment is not None:
        raise HTTPException(409, f"Claim {claim_id} has already been paid")
    if round(payment.amount, 2) != claim.decision.payout:
        raise HTTPException(
            409, f"The amount must match the approved payout of {claim.decision.payout}"
        )
    if claim.decision.payout > approval_limit(conn) and claim.sign_off is None:
        raise HTTPException(
            409,
            f"The payout is over the approval limit of {approval_limit(conn)}, "
            "so a handler must sign off before it is paid",
        )
    insert_payment(conn, claim_id, claim.decision.payout)
    return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, request: SignOffIn, conn: Db) -> Claim:
    """Sign off a large payout as a handler, which releases the payment."""
    claim = load_claim(conn, claim_id)
    handler = found(
        db.record(conn, "handler", request.handler_id), f"Handler {request.handler_id}"
    )
    if not handler["can_approve_over_limit"]:
        raise HTTPException(403, f"{handler['name']} cannot sign off large payouts")
    if claim.status != "awaiting_sign_off" or claim.decision is None:
        raise HTTPException(409, f"Claim {claim_id} is not waiting for sign-off")
    conn.execute(
        "INSERT INTO sign_offs VALUES (?, ?, ?)",
        (claim_id, request.handler_id, now()),
    )
    insert_payment(conn, claim_id, claim.decision.payout)
    conn.execute("UPDATE claims SET status = 'decided' WHERE claim_id = ?", (claim_id,))
    return load_claim(conn, claim_id)
