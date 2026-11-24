import runpy

from backend import db


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert claims[0]["claim_id"] == "CLM-1001"
    assert claims[0]["customer_name"] == "Maya Patel"
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0]["decision"] is None


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["amount_claimed"] == 420.0
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert claim["documents"][0]["type"] == "carrier_report"
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["payment"] is None


def test_unknown_ids(client):
    assert client.get("/api/claims/CLM-0000").status_code == 404
    assert client.get("/api/policies/POL-0000").status_code == 404
    response = client.get("/api/customers/CUS-0000/claims")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer CUS-0000 not found"


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["trip_cost"] == 3100.0
    assert policy["travelers"] == ["Maya Patel"]


def test_claim_history_has_no_personal_details(client):
    response = client.get("/api/customers/CUS-3001/claims")
    history = response.json()
    assert [claim["claim_id"] for claim in history] == ["CLM-0412"]
    assert "example.com" not in response.text
    assert "555" not in response.text


def test_get_plans(client):
    plans = client.get("/api/plans").json()
    assert [plan["plan"] for plan in plans["plans"]] == ["economy", "premium", "first"]
    assert plans["deductible_applies_to"] == ["baggage", "emergency_medical"]


def test_get_policy_wording(client):
    text = client.get("/api/policy-wording").json()["text"]
    assert text.startswith("# UnderCover Travel Insurance: Policy Wording")
    assert "Version 2026.1" in text


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [handler["handler_id"] for handler in handlers] == [
        "HND-01",
        "HND-02",
        "HND-03",
    ]
    assert "email" not in handlers[0]


def test_seed_resets_the_database(client):
    with db.connect() as conn:
        conn.execute("UPDATE claims SET status = 'decided'")
    runpy.run_module("backend.seed", run_name="__main__")
    claims = client.get("/api/claims").json()
    assert {claim["status"] for claim in claims} == {"waiting"}
