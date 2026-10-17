// Static checks for the single-file SPA in frontend/:
//  - every inline <script> parses
//  - manifest.json is valid JSON and references files that exist
//  - firebase.json rewrites keep /api/** pointed at Cloud Run
import { readFileSync, existsSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";

const root = new URL("../frontend/", import.meta.url).pathname;
const html = readFileSync(join(root, "index.html"), "utf8");
let failures = 0;
const fail = (msg) => { console.error(`✗ ${msg}`); failures++; };

const dir = mkdtempSync(join(tmpdir(), "spa-check-"));
const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)];
inline.forEach((m, i) => {
  const file = join(dir, `inline-${i}.js`);
  writeFileSync(file, m[1]);
  try {
    execFileSync(process.execPath, ["--check", file], { stdio: "pipe" });
  } catch (e) {
    fail(`inline script #${i} does not parse:\n${e.stderr}`);
  }
});
console.log(`✓ ${inline.length} inline script(s) parsed`);

// User/LLM-controlled text must go through esc() before reaching innerHTML.
const risky = /\$\{(?!esc\()[\w.]*\.(name|full_name|team_name|manager_name|news|reason|summary|message)(\|\|'[^']*')?\}/;
html.split("\n").forEach((line, i) => {
  if (/textContent|const text=|toast\(/.test(line)) return;
  if (risky.test(line)) fail(`index.html:${i + 1} interpolates text without esc(): ${line.trim().slice(0, 120)}`);
});

for (const f of ["sw.js"]) {
  try { execFileSync(process.execPath, ["--check", join(root, f)], { stdio: "pipe" }); }
  catch (e) { fail(`${f} does not parse:\n${e.stderr}`); }
}

const manifest = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
for (const icon of manifest.icons ?? []) {
  if (!existsSync(join(root, icon.src.replace(/^\//, "")))) fail(`manifest icon missing: ${icon.src}`);
}

const fb = JSON.parse(readFileSync(join(root, "firebase.json"), "utf8"));
const rewrites = fb.hosting?.rewrites ?? [];
if (!rewrites.some((r) => r.source === "/api/**" && r.run?.serviceId)) fail("firebase.json lost the /api/** → Cloud Run rewrite");

if (failures) process.exit(1);
console.log("✓ frontend checks passed");
