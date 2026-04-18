import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

function parseArgs(argv) {
  const options = {
    baseUrl: "http://127.0.0.1:8010",
    suitspec: "examples/suitspec.sample.json",
    sim: "sessions/body-sim.json",
    vrm: "viewer/assets/vrm/default.vrm",
    outputDir: "tests/.tmp/surface-first-demo",
    density: 72,
    shellOffset: 0.018,
    trackingSource: "vrm",
  };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === "--base-url" && next) {
      options.baseUrl = next;
      index += 1;
    } else if (token === "--suitspec" && next) {
      options.suitspec = next;
      index += 1;
    } else if (token === "--sim" && next) {
      options.sim = next;
      index += 1;
    } else if (token === "--vrm" && next) {
      options.vrm = next;
      index += 1;
    } else if (token === "--output-dir" && next) {
      options.outputDir = next;
      index += 1;
    } else if (token === "--density" && next) {
      options.density = Number(next);
      index += 1;
    } else if (token === "--shell-offset" && next) {
      options.shellOffset = Number(next);
      index += 1;
    } else if (token === "--tracking-source" && next) {
      options.trackingSource = String(next);
      index += 1;
    }
  }
  return options;
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function main() {
  const options = parseArgs(process.argv);
  const outputDir = path.resolve(options.outputDir);
  await ensureDir(outputDir);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });

  const url =
    `${options.baseUrl}/viewer/body-fit/` +
    `?suitspec=${encodeURIComponent(options.suitspec)}` +
    `&sim=${encodeURIComponent(options.sim)}` +
    `&vrm=${encodeURIComponent(options.vrm)}` +
    `&attach=vrm` +
    `&surfaceGraph=1&surfaceShell=1&surfaceMounts=1` +
    `&surfaceDensity=${encodeURIComponent(String(options.density))}` +
    `&surfaceOffset=${encodeURIComponent(String(options.shellOffset))}` +
    `&ts=${Date.now()}`;

  try {
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
      () => window.__HENSHIN_BODY_FIT__?.viewer?.vrm?.model && window.__HENSHIN_BODY_FIT__?.viewer?.meshes?.size === 18,
      null,
      { timeout: 90000 }
    );
    const summary = await page.evaluate(async ({ density, shellOffset, trackingSource }) => {
      return await window.__HENSHIN_BODY_FIT__.runSurfaceFirstDemo({
        graphVisible: true,
        shellVisible: true,
        mountsVisible: true,
        density,
        shellOffset,
        trackingSource,
      });
    }, { density: options.density, shellOffset: options.shellOffset, trackingSource: options.trackingSource });
    await page.evaluate(() => {
      const { viewer } = window.__HENSHIN_BODY_FIT__;
      viewer.setArmorVisible(false);
      viewer.setVrmVisible(false);
    });

    for (const view of [
      { name: "front", preset: "front" },
      { name: "side", preset: "side" },
    ]) {
      await page.evaluate((preset) => {
        window.__HENSHIN_BODY_FIT__.viewer.setCameraPreset(preset);
      }, view.preset);
      await page.waitForTimeout(240);
      await page.screenshot({
        path: path.join(outputDir, `${view.name}.png`),
        fullPage: true,
      });
    }

    const summaryPath = path.join(outputDir, "summary.json");
    await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2), "utf8");
    process.stdout.write(JSON.stringify({ ok: Boolean(summary?.sample_count), outputDir, summaryPath }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
