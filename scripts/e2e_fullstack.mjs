// Full-stack smoke: real API (pointed at scripts/mock_fpl.py) + real SPA in Chromium.
// Clicks every tab/sub-tab, imports demo team 1, optimises a squad, and fails on any
// page error, console error, failed API call, or empty panel.
//   make demo-up   # mock FPL on :8090 + API on :8001 (see Makefile)
//   node scripts/e2e_fullstack.mjs [--shots DIR]
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";
import { chromium } from "playwright";

const shots = process.argv.includes("--shots") ? process.argv[process.argv.indexOf("--shots") + 1] : null;
const root = new URL("../frontend/", import.meta.url).pathname;
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml" };
const server = createServer(async (req, res) => {
  const path = req.url.split("?")[0];
  try {
    res.writeHead(200, { "Content-Type": types[extname(path)] || "text/html" }).end(await readFile(join(root, path === "/" ? "index.html" : path)));
  } catch { res.writeHead(404).end(); }
}).listen(5000);  // must be an allowed CORS origin (see app/config.py); 3000 is the demo SPA
const port = 5000;

const browser = await chromium.launch(process.env.PLAYWRIGHT_CHROMIUM ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {});
const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error" && !/favicon|firebase|gstatic|fonts/.test(m.text())) problems.push(`console: ${m.text()}`); });
page.on("response", (r) => { if (r.url().includes(":8001/") && r.status() >= 400) problems.push(`HTTP ${r.status()} ${r.url()}`); });
// No third-party network in CI sandboxes: stub Firebase + fonts.
await page.route(/gstatic\.com\/firebasejs/, (r) => r.fulfill({ contentType: "text/javascript",
  body: "window.firebase={initializeApp(){},auth(){return{onAuthStateChanged(cb){setTimeout(()=>cb(null),0)},currentUser:null}}};" }));
await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ body: "" }));

const settle = () => page.waitForLoadState("networkidle").then(() => page.waitForTimeout(300));
async function check(name, selector, mustInclude) {
  await settle();
  const panel = page.locator(selector);
  if (!(await panel.count())) { problems.push(`${name}: ${selector} not rendered`); return; }
  // Wait for this panel's own spinners to clear (each tab loads independently).
  await page.waitForFunction((sel) => !document.querySelector(sel)?.querySelector(".loading, .spin"), selector, { timeout: 20000 })
    .catch(() => problems.push(`${name}: still loading after 20s`));
  const text = (await panel.innerText()).trim();
  const errEl = await panel.locator(".err").count();
  if (!text || errEl || (mustInclude && !mustInclude.test(text))) {
    problems.push(`${name}: panel ${selector} shows "${text.slice(0, 100).replace(/\s+/g, " ")}"`);
  } else console.log(`✓ ${name}`);
  if (shots) await page.screenshot({ path: `${shots}/${name.replace(/\W+/g, "-")}.png` });
}

await page.goto(`http://localhost:${port}/`);
await check("predictions", "#pred-grid", /\d/);
await check("captain picks", "#cap-row", /CAPTAIN/);
await check("gameweek bar (next deadline)", "#gwb-gw", /Gameweek 9/);

await page.click('#nav [data-tab="squad"], nav [data-tab="squad"] >> nth=0');
await page.fill("#tid-input", "1");
await page.evaluate(() => loadTeam());
await check("team import + briefing", "#team-content", /Demo XI/);
await check("briefing targets next GW", "#team-content .brief-title", /GW 9/);
if (await page.locator("#transfers-content").count()) await page.evaluate(() => loadTransfers(1));
await check("transfer suggestions", "#transfers-content", /↓/);
await page.evaluate(() => showSubtab("squad", "optimize"));
await page.evaluate(() => optimizeSquad());
await check("squad optimiser", "#squad-content", /STARTING XI/);
await page.evaluate(() => showSubtab("squad", "threegw"));
await check("3-GW planner", "#tgw-content", /\d/);

await page.evaluate(() => showTab("fixtures"));
await check("fixtures", "#fix-grid", /\w/);
await page.evaluate(() => showSubtab("fixtures", "fdr"));
await check("FDR heatmap", "#fdr-content", /Arsenal|Liverpool/);

await page.evaluate(() => showTab("intel"));
for (const [sub, sel] of [["trend", "#trend-content"], ["inj", "#inj-grid"], ["price", "#price-content"], ["value", "#value-grid"]]) {
  await page.evaluate((s) => showSubtab("intel", s), sub);
  await check(`intel/${sub}`, sel, /\d/);
}
await page.evaluate(() => showTab("search"));
await page.evaluate(() => doSearch("Liv"));
await check("search", "#sres", /Liv/);
await page.evaluate(() => showTab("gameweek"));
await check("gameweek", "#gw-content", /Gameweek|GW/);

await browser.close();
server.close();
if (problems.length) {
  console.error(problems.map((p) => `✗ ${p}`).join("\n"));
  process.exit(1);
}
console.log("✓ full-stack smoke passed");
