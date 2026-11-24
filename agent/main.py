"""The UnderCover Agent, which decides claims through the backend's API."""

import json
import os
import uuid
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend and return its JSON, raising on an error."""
    with backend() as client:
        response = client.request(method, path, json=body)
    response.raise_for_status()
    return response.json()


def call(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend for a tool, passing any refusal back to the model."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        return f"Error {response.status_code}: {response.json()['detail']}"
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim: the customer's story, the items claimed and the documents."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: the plan, add-ons, purchase date, trip and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's earlier claims."""
    return call("GET", f"/api/customers/{customer_id}/claims")


@tool
def get_plans() -> str:
    """Get the plans' limits, waiting periods and deductibles, and the add-ons."""
    return call("GET", "/api/plans")


@tool
def get_policy_wording() -> str:
    """Get the policy wording, which every decision must follow."""
    return call("GET", "/api/policy-wording")


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim, once. The payout is 0 unless approving."""
    body = {
        "decision": decision,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return call("POST", f"/api/claims/{claim_id}/decision", body)


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    get_plans,
    get_policy_wording,
    record_decision,
    pay_claim,
]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Describe a message from the agent as steps for the dashboard."""
    if isinstance(message, ToolMessage):
        return [("tool_result", f"{message.name}: {message.text}")]
    found = [("reply", str(message.text))] if message.text else []
    if isinstance(message, AIMessage):
        found += [
            ("tool_call", f"{tool_call['name']}({json.dumps(tool_call['args'])})")
            for tool_call in message.tool_calls
        ]
    return found


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, recording each step, and return its reply."""
    instructions = request("GET", "/api/instructions")["text"]
    request("POST", f"/api/claims/{claim_id}/start")
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    reply = ""
    for update in agent.stream(
        {"messages": [{"role": "user", "content": f"Please decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    ):
        for node in update.values():
            for message in node["messages"]:
                for kind, text in steps(message):
                    request(
                        "POST",
                        f"/api/claims/{claim_id}/steps",
                        {"kind": kind, "text": text},
                    )
                if isinstance(message, AIMessage) and message.text:
                    reply = str(message.text)
    return reply


def waiting_claims() -> list[str]:
    """Return the ids of the waiting claims, in queue order."""
    claims = request("GET", "/api/claims")
    return [claim["claim_id"] for claim in claims if claim["status"] == "waiting"]


def outcome(claim_id: str) -> str:
    """Describe where a claim stands after the agent has worked it."""
    claim = request("GET", f"/api/claims/{claim_id}")
    decision = claim["decision"]
    if decision is None:
        return f"{claim_id}: no decision recorded"
    line = f"{claim_id}: {decision['decision']}, ${decision['payout']:,.2f}"
    if claim["status"] == "awaiting_sign_off":
        return f"{line}, waiting for sign-off"
    return f"{line}, paid" if claim["payment"] else line


def work(claim_ids: list[str], llm: BaseChatModel | None = None) -> None:
    """Work the given claims, or every waiting claim, printing each outcome."""
    for claim_id in claim_ids or waiting_claims():
        run(claim_id, f"{claim_id}-{uuid.uuid4().hex[:8]}", llm)
        print(outcome(claim_id))
