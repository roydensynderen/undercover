import runpy

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend import db
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def stub(*replies: AIMessage) -> StubModel:
    return StubModel(messages=iter(replies))


def calls(*tool_calls: tuple[str, dict]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": f"call-{i}"}
            for i, (name, args) in enumerate(tool_calls)
        ],
    )


def decision(claim_id: str, payout: float) -> tuple[str, dict]:
    return (
        "record_decision",
        {
            "claim_id": claim_id,
            "decision": "approve",
            "payout": payout,
            "reason": "Covered by the policy.",
            "policy_section": "3. Trip Delay",
        },
    )


@pytest.fixture
def backend(client, monkeypatch):
    """Point the agent at a test backend on a fresh database."""
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    return client


def test_run_decides_and_pays(backend):
    llm = stub(
        calls(
            ("get_claim", {"claim_id": "CLM-1001"}),
            ("get_policy", {"policy_id": "POL-2001"}),
            ("get_claim_history", {"customer_id": "CUS-3001"}),
            ("get_plans", {}),
            ("get_policy_wording", {}),
        ),
        calls(decision("CLM-1001", 420.0)),
        calls(("pay_claim", {"claim_id": "CLM-1001", "amount": 420.0})),
        AIMessage(content="Approved, $420.00."),
    )
    assert main.run("CLM-1001", "thread-1", llm) == "Approved, $420.00."
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0
    steps = backend.get("/api/claims/CLM-1001/steps").json()
    kinds = [step["kind"] for step in steps]
    assert kinds.count("tool_call") == 7
    assert kinds.count("tool_result") == 7
    assert kinds[-1] == "reply"
    assert steps[0]["text"] == 'get_claim({"claim_id": "CLM-1001"})'
    assert any("Maya Patel" in step["text"] for step in steps)


def test_payment_over_the_limit_is_refused(backend):
    llm = stub(
        calls(decision("CLM-1002", 1250.0)),
        calls(("pay_claim", {"claim_id": "CLM-1002", "amount": 1250.0})),
        AIMessage(content="Approved, $1,250.00."),
    )
    main.run("CLM-1002", "thread-2", llm)
    claim = backend.get("/api/claims/CLM-1002").json()
    assert claim["status"] == "awaiting_sign_off"
    assert claim["payment"] is None
    results = [
        step["text"]
        for step in backend.get("/api/claims/CLM-1002/steps").json()
        if step["kind"] == "tool_result"
    ]
    assert results[-1].startswith("pay_claim: Error 409")
    assert (
        main.outcome("CLM-1002") == "CLM-1002: approve, $1,250.00, waiting for sign-off"
    )


def test_work_takes_only_waiting_claims_in_order(backend, capsys):
    with db.connect() as conn:
        conn.execute(
            "UPDATE claims SET status = 'decided' "
            "WHERE claim_id NOT IN ('CLM-1002', 'CLM-1004')"
        )
    main.work([], stub(AIMessage(content="Looking."), AIMessage(content="Looking.")))
    assert capsys.readouterr().out.splitlines() == [
        "CLM-1002: no decision recorded",
        "CLM-1004: no decision recorded",
    ]
    assert backend.get("/api/claims/CLM-1004").json()["status"] == "in_progress"


def test_work_one_claim(backend, capsys):
    llm = stub(calls(decision("CLM-1003", 0.0)), AIMessage(content="Done."))
    main.work(["CLM-1003"], llm)
    assert capsys.readouterr().out == "CLM-1003: approve, $0.00\n"
    assert backend.get("/api/claims/CLM-1001").json()["status"] == "waiting"


def test_command_line(monkeypatch):
    worked = []
    monkeypatch.setattr(main, "work", worked.append)
    monkeypatch.setattr("sys.argv", ["agent", "CLM-1001"])
    runpy.run_module("agent", run_name="__main__")
    assert worked == [["CLM-1001"]]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
