import { expect, type APIRequestContext } from "@playwright/test";

/** Has the agent's work on a claim recorded through the API, without a model. */
export async function decide(
  request: APIRequestContext,
  claimId: string,
  payout: number,
) {
  expect((await request.post(`/api/claims/${claimId}/start`)).ok()).toBe(true);
  for (const step of [
    { kind: "tool_call", text: `get_claim({"claim_id": "${claimId}"})` },
    { kind: "tool_result", text: `get_claim: {"claim_id": "${claimId}"}` },
  ]) {
    await request.post(`/api/claims/${claimId}/steps`, { data: step });
  }
  const decision = await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision: "approve",
      payout,
      reason: "The policy covers this loss.",
      policy_section: "5. Baggage and Personal Effects",
    },
  });
  expect(decision.ok()).toBe(true);
  return request.post(`/api/claims/${claimId}/payment`, {
    data: { amount: payout },
  });
}

export async function reply(request: APIRequestContext, claimId: string) {
  await request.post(`/api/claims/${claimId}/steps`, {
    data: { kind: "reply", text: "Done." },
  });
}
