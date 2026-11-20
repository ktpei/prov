import { execFileSync } from "node:child_process";
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
  await expect(page.getByText("Workbook range Model!B7:B8 attached")).toBeVisible();

  // Workbook question: proposal waits for approval, then export downloads.
  await page.getByRole("button", { name: Q2 }).click();
  await expect(page.getByText("1 proposed workbook change is waiting for your approval.")).toBeVisible();
  await expect(page.getByRole("tab", { name: /Changes/ })).toContainText("1");
  await expect(page.getByText("Awaiting approval")).toBeVisible();
  await page.getByRole("button", { name: "Approve 1 change and create copy" }).click();
  await expect(page.getByText("Edited copy ready")).toBeVisible();
  await expect(page.getByText("Input changes verified · existing formulas preserved")).toBeVisible();
  await expect(page.getByText(/Calculation pending/)).toBeVisible();
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


function syntheticWorkbook() {
  return execFileSync("uv", ["run", "python", "-c", `
import io, sys
from openpyxl import Workbook
book = Workbook()
book.active.title = "Inputs"
book.active["AA70"] = 125
book.active["AB70"] = "=AA70*2"
book.active["AC75"] = "End"
stream = io.BytesIO()
book.save(stream)
sys.stdout.buffer.write(stream.getvalue())
`], { cwd: ".." });
}

test("navigate distant ranges and inspect uncached formulas with keyboard", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByLabel("Upload an .xlsx workbook").setInputFiles({ name: "synthetic.xlsx", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: syntheticWorkbook() });
  await page.getByLabel("Go to range").fill("AA70:AC75");
  await page.getByRole("button", { name: "Go", exact: true }).click();
  await expect(page.locator('[data-cell="AA70"]')).toHaveText("125");
  await expect(page.locator('[data-cell="AB70"]')).toHaveText("Not calculated");
  await expect(page.getByText("Workbook range Inputs!AA70:AC75 attached")).toBeVisible();
  await page.locator('[data-cell="AA70"]').click();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator('[data-cell="AB70"]')).toBeFocused();
  await expect(page.getByLabel("Cell details")).toContainText("=AA70*2");
  await expect(page.getByLabel("Cell details")).toContainText("Unavailable");
  await expect(page.getByText("Workbook range Inputs!AB70 attached")).toBeVisible();
  await page.screenshot({ path: "/tmp/provenance-workbook-review.png", fullPage: true });
  await page.getByLabel("Go to range").fill("A0");
  await page.getByRole("button", { name: "Go", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Enter a valid range");
});

test("old workbook citations do not navigate a replacement upload", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByRole("button", { name: "Use the demo Cloudflare model" }).click();
  await page.locator('[data-cell="B7"]').click();
  await page.getByRole("button", { name: Q2 }).click();
  await expect(page.getByText("Awaiting approval")).toBeVisible();
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByLabel("Upload an .xlsx workbook").setInputFiles({ name: "synthetic.xlsx", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: syntheticWorkbook() });
  await expect(page.getByText("synthetic.xlsx", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Open source Model!B7/ }).first().click();
  await expect(page.getByText("This citation belongs to a previous upload. It cannot be located in the current workbook.")).toBeVisible();
  await expect(page.getByRole("table", { name: "Sheet Inputs" })).toBeVisible();
});

test("selected cell reaches chat before the turn starts and can be removed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByRole("button", { name: "Use the demo Cloudflare model" }).click();
  await page.locator('[data-cell="B7"]').click();
  await expect(page.getByText("Workbook range Model!B7 attached")).toBeVisible();
  await page.getByRole("tab", { name: "Evidence", exact: true }).click();
  await expect(page.getByText("Workbook range Model!B7 attached")).toBeVisible();

  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let contextSaved = false;
  let turnStarted = false;
  await page.route("**/context", async (route) => {
    if (route.request().method() === "PUT") {
      expect(route.request().postDataJSON()).toEqual({ sheet: "Model", range: "B7" });
      await gate;
      const response = await route.fetch();
      contextSaved = true;
      await route.fulfill({ response });
    } else await route.continue();
  });
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/turns")) {
      expect(contextSaved).toBe(true);
      turnStarted = true;
    }
  });
  await page.getByLabel("Question").fill(Q2);
  const saving = page.waitForRequest((request) => request.method() === "PUT" && request.url().endsWith("/context"));
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await saving;
  expect(turnStarted).toBe(false);
  release();
  await expect(page.getByText("Awaiting approval")).toBeVisible();
  expect(turnStarted).toBe(true);
  await page.getByRole("button", { name: /Remove/ }).click();
  await expect(page.getByText("Workbook range Model!B7 attached")).toHaveCount(0);
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await expect(page.getByText("Attached Model!B7", { exact: true })).toHaveCount(0);
});

test("context save failure preserves the question and prevents a contextless turn", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Workbook/ }).click();
  await page.getByRole("button", { name: "Use the demo Cloudflare model" }).click();
  await page.locator('[data-cell="B7"]').click();
  let turns = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/turns")) turns++;
  });
  await page.route("**/context", (route) => route.fulfill({
    status: 400, contentType: "application/json", body: JSON.stringify({ detail: "Context unavailable" }),
  }));
  await page.getByLabel("Question").fill(Q2);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Context unavailable");
  await expect(page.getByLabel("Question")).toHaveValue(Q2);
  expect(turns).toBe(0);
});
