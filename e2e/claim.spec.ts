import { expect, test } from "@playwright/test";
import { decide, reply } from "./api";

test("a decided claim shows the decision, its reasons and the steps", async ({
  page,
}) => {
  const payment = await decide(page.request, "CLM-1005", 243);
  expect(payment.ok()).toBe(true);
  await reply(page.request, "CLM-1005");
  await page.goto("/#/claims/CLM-1005");
  await expect(page.getByText("Decision: Approved")).toBeVisible();
  await expect(page.getByText("The policy covers this loss.")).toBeVisible();
  await expect(page.getByText("5. Baggage and Personal Effects")).toBeVisible();
  await expect(page.getByText("Paid $243.00")).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Agent steps" }).getByRole("listitem"),
  ).toHaveCount(3);
  await expect(page.locator(".title .badge")).toHaveText("Decided");
});

test("the agent's steps appear while it works", async ({ page }) => {
  await page.goto("/#/claims/CLM-1006");
  await expect(page.getByText("The agent has not started.")).toBeVisible();
  await page.request.post("/api/claims/CLM-1006/start");
  await page.request.post("/api/claims/CLM-1006/steps", {
    data: { kind: "tool_call", text: 'get_claim({"claim_id": "CLM-1006"})' },
  });
  await expect(
    page.getByText('get_claim({"claim_id": "CLM-1006"})'),
  ).toBeVisible();
  await expect(page.locator(".title .badge")).toHaveText("In progress");
});
