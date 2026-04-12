import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

function env(name, fallback = null) {
  const value = process.env[name];
  if (value == null || value === "") {
    if (fallback != null) return fallback;
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

async function launchBrowser() {
  const attempts = [
    { channel: process.env.HENSHIN_PLAYWRIGHT_CHANNEL || "msedge", headless: true },
    { channel: "chrome", headless: true },
    { headless: true },
  ];
  let lastError = null;
  for (const options of attempts) {
    try {
      return await chromium.launch(options);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("Unable to launch Chromium-compatible browser.");
}

async function main() {
  const timeoutMs = Number(env("HENSHIN_FIT_REGRESSION_TIMEOUT_MS", "90000"));
  const outputPath = env("HENSHIN_FIT_REGRESSION_OUTPUT");
  const payload = {
    suitspecPath: env("HENSHIN_FIT_REGRESSION_SUITSPEC"),
    simPath: env("HENSHIN_FIT_REGRESSION_SIM"),
    vrmPath: env("HENSHIN_FIT_REGRESSION_VRM"),
    mode: env("HENSHIN_FIT_REGRESSION_MODE", "auto_fit"),
    forceTPose: env("HENSHIN_FIT_REGRESSION_FORCE_TPOSE", "1") !== "0",
    attachMode: env("HENSHIN_FIT_REGRESSION_ATTACH_MODE", "vrm"),
  };

  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await page.goto(env("HENSHIN_FIT_REGRESSION_URL"), {
      waitUntil: "domcontentloaded",
      timeout: timeoutMs,
    });
    await page.waitForFunction(() => typeof window.__HENSHIN_BODY_FIT__?.runFitRegression === "function", {
      timeout: timeoutMs,
    });
    const result = await page.evaluate(async (input) => {
      return window.__HENSHIN_BODY_FIT__.runFitRegression(input);
    }, payload);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf-8");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
