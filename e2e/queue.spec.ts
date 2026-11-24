import { expect, test } from "@playwright/test";

test("the queue lists every claim with where it stands", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(25);
  const counts = page.getByRole("list", { name: "Claims by state" });
  await expect(counts.getByRole("listitem")).toHaveCount(4);
  const numbers = await counts.locator(".number").allInnerTexts();
  expect(numbers.reduce((sum, n) => sum + Number(n), 0)).toBe(25);
});

test("a claim opens from the queue", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByText(/My flight home from Rome/)).toBeVisible();
  await expect(
    page.getByText("Meridian Air cancellation notice"),
  ).toBeVisible();
  await expect(page.getByText("POL-2001")).toBeVisible();
  await expect(
    page.getByText(/Checked bag arrived 30 hours late/),
  ).toBeVisible();
});
