import { expect, test } from "@playwright/test";
import { decide, reply } from "./api";

test("a payout over the limit waits for a handler's sign-off", async ({
  page,
}) => {
  const payment = await decide(page.request, "CLM-1008", 2440);
  expect(payment.status()).toBe(409);
  await reply(page.request, "CLM-1008");
  await page.goto("/#/claims/CLM-1008");
  await expect(page.locator(".title .badge")).toHaveText(
    "Waiting for sign-off",
  );
  await expect(page.getByText("Not paid")).toBeVisible();
  await page.getByRole("combobox", { name: "Handler" }).selectOption("HND-03");
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(page.getByText("Paid $2,440.00")).toBeVisible();
  await expect(page.getByText("Priya Raman")).toBeVisible();
  await expect(page.locator(".title .badge")).toHaveText("Decided");
  await expect(page.getByText("Sign-off needed")).toBeHidden();
});
