import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { stubApi, summary } from "./stubs";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const claims = [
  summary(),
  summary({
    claim_id: "CLM-1002",
    customer_name: "Leo Brandt",
    status: "decided",
    decision: "approve",
    payout: 1250,
  }),
  summary({ claim_id: "CLM-1003", status: "awaiting_sign_off" }),
];

it("lists the claims with where each stands", async () => {
  stubApi({ "GET /api/claims": claims });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1002" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1002");
  const row = link.closest("tr");
  if (!row) throw new Error("no row");
  expect(within(row).getByText("Leo Brandt")).toBeDefined();
  expect(within(row).getByText("Approved")).toBeDefined();
  expect(within(row).getByText("$1,250.00")).toBeDefined();
  expect(within(row).getByText("Decided")).toBeDefined();
  expect(screen.getAllByText("Trip delay")).toHaveLength(3);
});

it("counts the claims in each state", async () => {
  stubApi({ "GET /api/claims": claims });
  render(<Queue />);
  const counts = await screen.findByRole("list", { name: "Claims by state" });
  expect(counts.textContent).toBe(
    "1Waiting0In progress1Waiting for sign-off1Decided",
  );
});

it("shows an error when the backend fails", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<Queue />);
  expect(await screen.findByText("Error: offline")).toBeDefined();
});

it("refreshes while claims are still open", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const routes: Record<string, unknown> = { "GET /api/claims": [summary()] };
  const fetchMock = stubApi(routes);
  render(<Queue />);
  await screen.findByText("Waiting", { selector: ".badge" });
  routes["GET /api/claims"] = [summary({ status: "decided" })];
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(
    await screen.findByText("Decided", { selector: ".badge" }),
  ).toBeDefined();
  await act(() => vi.advanceTimersByTimeAsync(6000));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
