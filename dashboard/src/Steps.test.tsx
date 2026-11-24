import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Steps } from "./Steps";
import { steps } from "./stubs";

afterEach(cleanup);

it("lists the agent's steps in order", () => {
  render(<Steps steps={steps} working={false} />);
  const items = within(screen.getByRole("list", { name: "Agent steps" }))
    .getAllByRole("listitem")
    .map((item) => item.textContent);
  expect(items).toEqual([
    '09:57:01Tool callget_claim({"claim_id": "CLM-1001"})',
    '09:57:02Resultget_claim: {"claim_id": "CLM-1001"}',
    "09:57:09ReplyApproved, $420.00.",
  ]);
});

it("folds a long result away", () => {
  const long = "get_policy_wording: " + "x".repeat(300);
  render(
    <Steps
      steps={[{ step_id: 1, kind: "tool_result", text: long, at: "" }]}
      working
    />,
  );
  expect(screen.getByText(long)).toBeDefined();
  expect(screen.getByText(`${long.slice(0, 120)}…`)).toBeDefined();
  expect(screen.getByText("Working")).toBeDefined();
});

it("says when the agent has not started", () => {
  render(<Steps steps={[]} working={false} />);
  expect(screen.getByText("The agent has not started.")).toBeDefined();
});

it("says when the agent is starting", () => {
  render(<Steps steps={[]} working />);
  expect(screen.getByText("The agent is starting.")).toBeDefined();
});
