import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, claimRoutes, stubApi } from "./stubs";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const decision = {
  decision: "approve" as const,
  payout: 1250,
  reason: "The bag was lost by the airline.",
  policy_section: "5. Baggage and Personal Effects",
  decided_at: "2026-11-24T09:57:07+00:00",
};
const waiting = claim({ status: "awaiting_sign_off", decision });
const signedOff: Claim = {
  ...waiting,
  status: "decided",
  sign_off: {
    handler_id: "HND-01",
    handler_name: "Dana Whitfield",
    signed_at: "2026-11-24T10:00:00+00:00",
  },
  payment: { amount: 1250, paid_at: "2026-11-24T10:00:00+00:00" },
};

it("offers only the handlers who can sign off", async () => {
  stubApi(claimRoutes(waiting));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Sign-off needed")).toBeDefined();
  expect(screen.getByText("Not paid")).toBeDefined();
  const select = screen.getByRole("combobox", { name: "Handler" });
  await within(select).findByText("Dana Whitfield, Senior Claims Handler");
  expect(within(select).queryByText(/Trainee/)).toBeNull();
});

it("signs off and shows the payment", async () => {
  const routes = claimRoutes(waiting);
  const fetchMock = stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByText("Dana Whitfield, Senior Claims Handler");
  routes["POST /api/claims/CLM-1001/sign-off"] = signedOff;
  routes["GET /api/claims/CLM-1001"] = signedOff;
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect(await screen.findByText("Paid $1,250.00")).toBeDefined();
  expect(screen.getByText("Dana Whitfield")).toBeDefined();
  expect(screen.queryByText("Sign-off needed")).toBeNull();
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(post?.[1]?.body).toBe('{"handler_id":"HND-01"}');
});

it("shows why a sign-off was refused", async () => {
  stubApi({
    ...claimRoutes(waiting),
    "POST /api/claims/CLM-1001/sign-off": Response.json(
      { detail: "Trainee cannot sign off large payouts" },
      { status: 403 },
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByText("Dana Whitfield, Senior Claims Handler");
  fireEvent.change(screen.getByRole("combobox", { name: "Handler" }), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect(
    await screen.findByText("Trainee cannot sign off large payouts"),
  ).toBeDefined();
  expect(
    screen
      .getByRole("button", { name: "Sign off and pay" })
      .hasAttribute("disabled"),
  ).toBe(false);
});

it("reports a failure without a reason", async () => {
  stubApi({
    ...claimRoutes(waiting),
    "POST /api/claims/CLM-1001/sign-off": Response.json(
      { detail: [{ msg: "bad" }] },
      { status: 422 },
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByText("Dana Whitfield, Senior Claims Handler");
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect(await screen.findByText("The request failed (422)")).toBeDefined();
});
