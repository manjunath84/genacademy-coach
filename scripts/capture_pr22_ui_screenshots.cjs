#!/usr/bin/env node
/* eslint-disable no-console */

const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const BASE_URL = process.env.GENACADEMY_COACH_UI_URL || "http://127.0.0.1:7861";
const OUT_DIR =
  process.env.GENACADEMY_COACH_SCREENSHOT_DIR ||
  path.join(process.cwd(), "docs/assets/pr22-ui-screenshots");
const CAPTURE_MODES = new Set(
  (process.env.GENACADEMY_COACH_CAPTURE_MODES || "teach,quiz")
    .split(",")
    .map((mode) => mode.trim())
    .filter(Boolean),
);

async function save(page, name) {
  const file = path.join(OUT_DIR, name);
  await page.screenshot({ path: file, fullPage: true });
  console.log(file);
}

async function openApp(page) {
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
}

async function clickTab(page, label) {
  await page.evaluate(() => window.scrollTo(0, 0));
  const tab = page
    .locator('button[role="tab"]')
    .filter({ hasText: new RegExp(`^${label}$`) })
    .first();
  await tab.waitFor({ state: "visible" });
  await tab.click({ force: true });
  await page.waitForTimeout(500);
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  page.setDefaultTimeout(180000);

  try {
    await openApp(page);

    if (CAPTURE_MODES.has("teach")) {
      await page.getByRole("button", { name: /^Grounded preset$/ }).click();
      await page.getByRole("button", { name: /^Run teach$/ }).click();
      await page.getByText("Turn 1").first().waitFor();
      await page.getByText("Turn 2").first().waitFor();
      await page.getByText(/re_explain_differently|TURN 2/).first().waitFor();
      await save(page, "desktop-1440x1000-teach-grounded-output.png");

      await page.getByRole("button", { name: /^Refusal preset$/ }).click();
      await page.getByRole("button", { name: /^Run teach$/ }).click();
      await page
        .getByText(/refuse_escalate|cannot find|can't find|could not find/i)
        .first()
        .waitFor();
      await save(page, "desktop-1440x1000-teach-refusal-output.png");
    }

    if (CAPTURE_MODES.has("quiz")) {
      await openApp(page);
      await clickTab(page, "Quiz");
      await page.getByRole("button", { name: /^Grounded quiz preset$/ }).click();
      await page.getByRole("button", { name: /^Run quiz$/ }).click();
      await page.getByText(/Question text is hidden by default/i).waitFor();
      await page.getByText(/Score:/i).waitFor();
      await save(page, "desktop-1440x1000-quiz-hidden-output.png");

      await openApp(page);
      await clickTab(page, "Quiz");
      await page.getByLabel(/Show generated quiz questions/i).check();
      await page.waitForTimeout(600);
      await save(page, "desktop-1440x1000-quiz-reveal-control-no-output.png");
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
