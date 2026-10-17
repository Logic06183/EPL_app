// Browser regression tests for the SPA. Serves frontend/ itself and fakes the API.
//  1. hostile FPL team / player / Gemini text must render as text (stored XSS)
//  2. API errors show useful messages; a Pro-gated 403 opens the upgrade modal
//   npm i -D playwright && npx playwright install chromium   (or PLAYWRIGHT_CHROMIUM=/path/to/chrome)
//   node scripts/e2e.mjs
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";
import { chromium } from "playwright";

const root = new URL("../frontend/", import.meta.url).pathname;
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml" };
const server = createServer(async (req, res) => {
  const path = req.url.split("?")[0];
  try {
    const body = await readFile(join(root, path === "/" ? "index.html" : path));
    res.writeHead(200, { "Content-Type": types[extname(path)] || "text/html" }).end(body);
  } catch {
    res.writeHead(404).end();
  }
}).listen(0);
const port = server.address().port;

const PAY = '<img src=x onerror="window.__pwned=1">';
const team = {
  team_name: PAY, manager_name: PAY, gameweek: 7, gameweek_points: 50, overall_points: 400, overall_rank: 1, team_value: 100,
  picks: [{ id: 1, name: PAY, team_name: PAY, position_name: "MID", price: 8.5, is_starting: true, is_captain: true, total_points: 5, news: PAY }],
};
const briefing = {
  team_id: 1, gameweek: 7, summary: PAY,
  alerts: [{ player_id: 1, name: PAY, team_name: PAY, flag: "DOUBT", news: PAY, reason: PAY }],
  captain: { player_id: 1, name: PAY, team_name: PAY, predicted_points: 6, reason: PAY, currently_captained: true },
};

const browser = await chromium.launch(process.env.PLAYWRIGHT_CHROMIUM ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {});
let failures = 0;
const fail = (m) => { console.error(`✗ ${m}`); failures++; };

async function newPage(apiHandler) {
  const ctx = await browser.newContext({ serviceWorkers: "block" });
  const page = await ctx.newPage();
  await page.route(/localhost:8001\//, apiHandler);
  await page.route(/gstatic\.com\/firebasejs/, (r) =>
    r.fulfill({ contentType: "text/javascript", body: "window.firebase={initializeApp(){},auth(){return{onAuthStateChanged(cb){setTimeout(()=>cb(null),0)},currentUser:null}}};" }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ body: "" }));
  await page.goto(`http://localhost:${port}/`);
  return page;
}

// ── 1. XSS ───────────────────────────────────────────────────────────────────
{
  const page = await newPage((r) => {
    const u = r.request().url();
    const body = u.includes("/briefing") ? briefing : u.includes("/fpl-team/") ? team : {};
    r.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.evaluate(() => { document.getElementById("tid-input").value = "123"; });
  await page.evaluate(() => loadTeam());
  await page.waitForSelector("#team-content .team-card", { state: "attached", timeout: 10000 });
  const html = await page.locator("#team-content").innerHTML();
  if (await page.evaluate(() => window.__pwned) || /<img/.test(html)) fail("XSS payload executed or rendered as HTML");
  else if (!html.includes("&lt;img")) fail("payload text not shown — XSS test did not exercise rendering");
  else console.log("✓ hostile team data rendered as text");
  await page.context().close();
}

// ── 2. Error states ──────────────────────────────────────────────────────────
const cases = [
  ["429", (r) => r.fulfill({ status: 429, contentType: "application/json", body: JSON.stringify({ detail: "Too many requests — please wait a moment and try again." }) }), /Too many requests/],
  ["500", (r) => r.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "Internal server error" }) }), /went wrong on our side/],
  ["network", (r) => r.abort(), /Could not reach the server|offline/],
];
for (const [name, handler, expected] of cases) {
  const page = await newPage((r) => (r.request().url().includes("/players/predictions") ? handler(r) : r.fulfill({ body: "{}" })));
  await page.evaluate(() => loadPred());
  const text = await page.locator("#pred-grid").innerText();
  if (!expected.test(text)) fail(`${name}: predictions error shows "${text.slice(0, 80)}"`);
  else console.log(`✓ ${name} error message: ${text.trim().slice(0, 60)}`);
  await page.context().close();
}
{
  const page = await newPage((r) => r.request().url().includes("/players/captain")
    ? r.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ detail: { error: "upgrade_required", message: "Upgrade", plan: "free" } }) })
    : r.fulfill({ body: "{}" }));
  await page.evaluate(() => apiFetch("/players/captain").catch(() => {}));
  const hidden = await page.locator("#upgrade-modal").evaluate((el) => el.classList.contains("hidden"));
  if (hidden) fail("403 upgrade_required did not open the upgrade modal");
  else console.log("✓ Pro-gated 403 opens the upgrade modal");
  await page.context().close();
}

{
  // Launch grace: the API says anonymous users get Pro → captain picks must render, not a lock.
  const page = await newPage((r) => {
    const u = r.request().url();
    const body = u.includes("/users/me") ? { authenticated: false, plan: "free", effective_plan: "pro" }
      : u.includes("/players/captain") ? { captain_picks: [{ name: "Salah", team_name: "Liverpool", predicted_points: 8.1 }] } : {};
    r.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.waitForTimeout(1500);
  const capRow = await page.locator("#cap-row").innerText();
  if (!capRow.includes("Salah")) fail(`grace-period anon user sees "${capRow.slice(0, 60)}" instead of captain picks`);
  else console.log("✓ grace-period anonymous user gets Pro features");
  await page.context().close();
}

{
  // Dialogs: focus moves in, Escape closes, focus returns to the opener.
  const page = await newPage((r) => r.fulfill({ body: "{}" }));
  await page.waitForTimeout(500);
  await page.click("#auth-btn");
  await page.waitForTimeout(100);
  const inside = await page.evaluate(() => !!document.activeElement?.closest("#signin-modal"));
  await page.keyboard.press("Escape");
  const closed = await page.locator("#signin-modal").evaluate((el) => el.classList.contains("hidden"));
  await page.waitForTimeout(50);
  const back = await page.evaluate(() => document.activeElement?.id);
  if (!inside || !closed || back !== "auth-btn") fail(`dialog keyboard: focusInside=${inside} escCloses=${closed} focusReturnedTo=${back}`);
  else console.log("✓ dialog focus management + Escape");
  await page.context().close();
}

await browser.close();
server.close();
if (failures) process.exit(1);
