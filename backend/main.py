"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Decision,
    Handler,
    Payment,
    Plans,
    Policy,
    PreviousClaim,
    SignOff,
    Text,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)
Db = Annotated[sqlite3.Connection, Depends(db.database)]


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
    return Plans.model_validate(db.record(conn, "settings", "plans"))


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording, the contract with the customer."""
    return Text(text=(db.DATA / "policy_wording.md").read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: Db) -> list[Handler]:
    """List the claims handlers and whether each can sign off large payouts."""
    return [Handler(**handler) for handler in db.records(conn, "handler")]
