import { expect, it } from "vitest";
import { finished, label, money } from "./format";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
});

it("turns codes into labels", () => {
  expect(label("trip_delay")).toBe("Trip delay");
});

it("knows when the agent has finished a claim", () => {
  expect(finished("decided")).toBe(true);
  expect(finished("awaiting_sign_off")).toBe(true);
  expect(finished("in_progress")).toBe(false);
  expect(finished("waiting")).toBe(false);
});
