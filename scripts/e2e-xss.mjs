// Browser regression test: hostile FPL team / player / Gemini text must render as text.
// Serves frontend/ itself, fakes the API, imports a team whose every string is an XSS payload.
//   npm i -D playwright && npx playwright install chromium   (or PLAYWRIGHT_CHROMIUM=/path/to/chrome)
//   node scripts/e2e-xss.mjs
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
const ctx = await browser.newContext({ serviceWorkers: "block" });
const page = await ctx.newPage();
await page.route(/localhost:8001\//, (r) => {
  const u = r.request().url();
  const body = u.includes("/briefing") ? briefing : u.includes("/fpl-team/") ? team : {};
  r.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
});
await page.route(/gstatic\.com\/firebasejs/, (r) =>
  r.fulfill({ contentType: "text/javascript", body: "window.firebase={initializeApp(){},auth(){return{onAuthStateChanged(){},currentUser:null}}};" }));
await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ body: "" }));

await page.goto(`http://localhost:${port}/`);
await page.evaluate(() => { document.getElementById("tid-input").value = "123"; });
await page.evaluate(() => loadTeam());
await page.waitForSelector("#team-content .team-card", { state: "attached", timeout: 10000 });
const html = await page.locator("#team-content").innerHTML();
const pwned = await page.evaluate(() => window.__pwned);
await browser.close();
server.close();

if (pwned || /<img/.test(html)) {
  console.error("✗ XSS payload executed or rendered as HTML");
  process.exit(1);
}
if (!html.includes("&lt;img")) {
  console.error("✗ payload text not shown — test did not exercise rendering");
  process.exit(1);
}
console.log("✓ hostile team data rendered as text");
