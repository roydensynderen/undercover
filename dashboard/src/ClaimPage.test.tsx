import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClaimPage } from "./ClaimPage";
import { claim, claimRoutes, stubApi } from "./stubs";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const decided = claim({
  status: "decided",
  decision: {
    decision: "approve",
    payout: 420,
    reason: "The delay was covered.",
    policy_section: "3. Trip Delay",
    decided_at: "2026-11-24T09:57:07+00:00",
  },
  payment: { amount: 420, paid_at: "2026-11-24T09:57:08+00:00" },
});

it("shows the claim in full", async () => {
  stubApi(claimRoutes(claim()));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("$420.00")).toBeDefined();
  expect(screen.getByText("Cancellation notice")).toBeDefined();
  expect(
    screen.getByText("The agent has not decided this claim yet."),
  ).toBeDefined();
  expect(await screen.findByText("Premium")).toBeDefined();
  expect(screen.getByText("Electronics plus")).toBeDefined();
  expect(
    await screen.findByText(/Checked bag arrived 30 hours late/),
  ).toBeDefined();
});

it("shows the agent's decision and its reasons", async () => {
  stubApi(claimRoutes(decided));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Decision: Approved")).toBeDefined();
  expect(screen.getByText("The delay was covered.")).toBeDefined();
  expect(screen.getByText("3. Trip Delay")).toBeDefined();
  expect(screen.getByText("Paid $420.00")).toBeDefined();
});

it("shows a decline with no payment", async () => {
  stubApi(
    claimRoutes(
      claim({
        status: "decided",
        decision: {
          decision: "decline",
          payout: 0,
          reason: "Not covered.",
          policy_section: "9. General exclusions",
          decided_at: "2026-11-24T09:57:07+00:00",
        },
      }),
    ),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Decision: Declined")).toBeDefined();
  expect(screen.getByText("None")).toBeDefined();
});

it("says when there is no earlier claim", async () => {
  stubApi({
    ...claimRoutes(claim()),
    "GET /api/customers/CUS-3001/claims": [],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("No earlier claims.")).toBeDefined();
});

it("shows an error for an unknown claim", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-0000" />);
  expect(
    await screen.findByText("Error: No stub for GET /api/claims/CLM-0000"),
  ).toBeDefined();
});

it("refreshes until the agent has decided", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const routes = claimRoutes(claim({ status: "in_progress" }));
  const fetchMock = stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByText("In progress", { selector: ".badge" });
  routes["GET /api/claims/CLM-1001"] = decided;
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(await screen.findByText("Decision: Approved")).toBeDefined();
  const calls = fetchMock.mock.calls.length;
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(fetchMock.mock.calls).toHaveLength(calls);
});
