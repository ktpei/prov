import { expect, test } from "@playwright/test";

const Q1 = "What revenue did Cloudflare report for Q3 2024, and what full-year 2024 revenue guidance did management give?";
const Q2 = "Does the FY2024 revenue assumption in my model match management's latest guidance? If not, propose an update.";

test("full analyst loop in scripted replay", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => message.type() === "error" && errors.push(message.text()));
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");
  await expect(page.getByRole("radio", { name: "Scripted replay" })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("radio", { name: "Live model" })).toBeDisabled();

  // Research question: streamed activity, cited answer, evidence opens at the cited line.
  await page.getByRole("button", { name: Q1 }).click();
  await expect(page.getByText("Cited answer")).toBeVisible();
  await expect(page.getByText("Scripted replay, no model call")).toBeVisible();
  await expect(page.locator("td", { hasText: "430.1" })).toBeVisible();
  await expect(page.locator("mark.quote", { hasText: "Total revenue of $430.1 million" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Public source" })).toHaveAttribute("href", /cloudflare\.net/);

  await page.getByRole("tab", { name: "Activity" }).click();
  await expect(page.getByText("Run completed")).toBeVisible();
  await expect(page.getByText(/^Read/).first()).toBeVisible();

  // Second citation opens the guidance line.
  await page.getByRole("button", { name: /Open source Q3 release L63/ }).first().click();
  await expect(page.locator("mark.quote", { hasText: "Total revenue of $1,661.0 to $1,662.0 million" })).toBeVisible();

  // Workbook: demo model, range selection, attach.
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByRole("button", { name: "Use the demo Cloudflare model" }).click();
  await expect(page.locator('td[title="B7"]')).toHaveText("1,650.0");
  await expect(page.locator('td[title^="B9"]')).toHaveText("13.0%");
  await page.locator('td[title="B7"]').click();
  await page.locator('td[title="B8"]').click({ modifiers: ["Shift"] });
  await page.getByRole("button", { name: "Attach to next question" }).click();
  await expect(page.getByText("Workbook range Model!B7:B8 attached")).toBeVisible();

  // Workbook question: proposal waits for approval, then export downloads.
  await page.getByRole("button", { name: Q2 }).click();
  await expect(page.getByText("1 proposed workbook change is waiting for your approval.")).toBeVisible();
  await expect(page.getByRole("tab", { name: /Changes/ })).toContainText("1");
  await expect(page.getByText("Awaiting approval")).toBeVisible();
  await page.getByRole("button", { name: "Approve 1 change and create copy" }).click();
  await expect(page.getByText("Edited copy ready")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download edited copy" }).click();
  expect((await download).suggestedFilename()).toMatch(/cloudflare-fy2024-model-provenance-\d+\.xlsx$/);
  await expect(page.getByText("Approved changes are in the edited copy below.")).toBeVisible();

  // Workbook citation chip opens the cell.
  await page.getByRole("button", { name: /Open source Model!B7/ }).first().click();
  await expect(page.getByRole("tab", { name: /Workbook/ })).toHaveAttribute("aria-selected", "true");

  expect(errors).toEqual([]);
});

test("unscripted replay questions explain what to do", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Question").fill("What is Cloudflare's dividend policy?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("alert")).toContainText("No scripted replay for this question");
  await expect(page.getByLabel("Question")).toHaveValue("What is Cloudflare's dividend policy?");
});

test("double-clicking a starter runs it once without an error", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: Q1 }).dblclick();
  await expect(page.getByText("Cited answer")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.locator("section[aria-label^='Question']")).toHaveCount(1);
});

test("replay mode shows only scripted starters", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Scripted replay covers only the questions below.")).toBeVisible();
  await expect(page.getByRole("button", { name: /go-to-market/ })).toHaveCount(0);
  await page.locator("select").selectOption("earnings-excerpts");
  await expect(page.getByText("This evidence set has no scripted questions yet.")).toBeVisible();
});
