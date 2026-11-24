import json

import pytest

from backend import db

REASON = "The delay was covered. We pay the costs claimed."


def decide(client, claim_id, decision="approve", payout=420.0):
    client.post(f"/api/claims/{claim_id}/start")
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": REASON,
            "policy_section": "3. Trip Delay",
        },
    )


def pay(client, claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def test_start_claim(client):
    claim = client.post("/api/claims/CLM-1001/start").json()
    assert claim["status"] == "in_progress"
    assert client.post("/api/claims/CLM-1001/start").status_code == 200


def test_cannot_restart_a_decided_claim(client):
    decide(client, "CLM-1001")
    response = client.post("/api/claims/CLM-1001/start")
    assert response.status_code == 409


def test_steps(client):
    client.post("/api/claims/CLM-1001/steps", json={"kind": "tool_call", "text": "a"})
    client.post("/api/claims/CLM-1001/steps", json={"kind": "reply", "text": "b"})
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [(step["kind"], step["text"]) for step in steps] == [
        ("tool_call", "a"),
        ("reply", "b"),
    ]
    assert client.get("/api/claims/CLM-1002/steps").json() == []
    bad = client.post("/api/claims/CLM-1001/steps", json={"kind": "x", "text": "c"})
    assert bad.status_code == 422


def test_small_approval_is_decided_and_paid(client):
    claim = decide(client, "CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["decision"]["payout"] == 420.0
    assert claim["decision"]["policy_section"] == "3. Trip Delay"
    paid = pay(client, "CLM-1001", 420.0).json()
    assert paid["payment"]["amount"] == 420.0
    summary = client.get("/api/claims").json()[0]
    assert (summary["status"], summary["decision"], summary["payout"]) == (
        "decided",
        "approve",
        420.0,
    )


def test_large_approval_waits_for_sign_off(client):
    claim = decide(client, "CLM-1002", payout=1250.0).json()
    assert claim["status"] == "awaiting_sign_off"
    response = pay(client, "CLM-1002", 1250.0)
    assert response.status_code == 409
    assert "a handler must sign off" in response.json()["detail"]
    assert client.get("/api/claims/CLM-1002").json()["payment"] is None


def test_sign_off_releases_the_payment(client):
    decide(client, "CLM-1002", payout=1250.0)
    claim = client.post(
        "/api/claims/CLM-1002/sign-off", json={"handler_id": "HND-01"}
    ).json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["payment"]["amount"] == 1250.0
    assert pay(client, "CLM-1002", 1250.0).status_code == 409


def test_sign_off_needs_a_handler_who_can(client):
    with db.connect() as conn:
        handler = {
            "handler_id": "HND-09",
            "name": "Trainee",
            "role": "Trainee",
            "email": "trainee@undercover.example",
            "can_approve_over_limit": False,
        }
        conn.execute(
            "INSERT INTO records VALUES ('handler', 'HND-09', ?)",
            (json.dumps(handler),),
        )
    decide(client, "CLM-1002", payout=1250.0)
    response = client.post(
        "/api/claims/CLM-1002/sign-off", json={"handler_id": "HND-09"}
    )
    assert response.status_code == 403
    unknown = client.post(
        "/api/claims/CLM-1002/sign-off", json={"handler_id": "HND-00"}
    )
    assert unknown.status_code == 404
    assert client.get("/api/claims/CLM-1002").json()["status"] == "awaiting_sign_off"


def test_sign_off_only_when_waiting(client):
    decide(client, "CLM-1001")
    response = client.post(
        "/api/claims/CLM-1001/sign-off", json={"handler_id": "HND-01"}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_cannot_pay_a_claim_that_is_not_approved(client, decision):
    claim = decide(client, "CLM-1001", decision=decision, payout=0).json()
    assert claim["status"] == "decided"
    assert pay(client, "CLM-1001", 420.0).status_code == 409


def test_cannot_pay_before_a_decision(client):
    assert pay(client, "CLM-1001", 420.0).status_code == 409


def test_payment_must_match_and_happen_once(client):
    decide(client, "CLM-1001")
    assert pay(client, "CLM-1001", 500.0).status_code == 409
    assert pay(client, "CLM-1001", 420.0).status_code == 200
    assert pay(client, "CLM-1001", 420.0).status_code == 409


def test_decision_rules(client):
    assert decide(client, "CLM-1001", decision="decline", payout=50).status_code == 422
    assert decide(client, "CLM-1001", decision="maybe").status_code == 422
    assert decide(client, "CLM-1001", payout=-1).status_code == 422
    assert decide(client, "CLM-1001").status_code == 200
    second = client.post(
        "/api/claims/CLM-1001/decision",
        json={
            "decision": "decline",
            "payout": 0,
            "reason": REASON,
            "policy_section": "9",
        },
    )
    assert second.status_code == 409


def test_get_instructions(client):
    text = client.get("/api/instructions").json()["text"]
    assert text.startswith("You are the UnderCover Agent")
