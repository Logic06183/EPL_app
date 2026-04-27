# Design Audit — EPL AI Pro
**Site:** https://epl-prediction-app.web.app  
**Date:** 2026-04-27  
**Reviewer:** /design-review (gstack)  
**Branch:** main  
**Scope:** Full site — 5 tabs (Predictions, My Squad, Fixtures & FDR, Intel, Gameweek)

---

## Design Score: C+  
## AI Slop Score: C

---

## Category Grades

| Category | Grade | Key Issue |
|---|---|---|
| Visual Hierarchy | B- | Paywall dominates above-the-fold for free users |
| Typography | C | 12px nav tabs, 10-13px stat labels, body line-height: normal |
| Color & Contrast | B+ | Good dark palette, missing color-scheme: dark declaration |
| Spacing & Layout | C+ | 6 non-systematic border-radius values, 13px card padding not on 8px grid |
| Interaction States | C | Sign In + Go Pro buttons are 30px tall (below 44px minimum) |
| Responsive | B | Works at all breakpoints, tablet nav has float issue |
| Content Quality | B- | Instructions compensating for UX failures, placeholder-as-label |
| AI Slop | C | Emoji in all 6 nav tabs + header bar + section headings |
| Motion | C+ | `transition: all` on cards, no `prefers-reduced-motion` check |
| Performance | A | 641ms total load, no console errors — excellent |

---

## First Impression

"The site communicates: **sports data tool with a premium-tier model**."

"I notice: **a large lock icon with PRO FEATURE text is the first visually dominant element above the fold for non-logged-in users**."

"The first 3 things my eye goes to are: **(1) the PRO FEATURE paywall block** (center stage, immediately above the player grid), **(2) the player prediction cards** grid below it, **(3) the nav tabs** with the active underline."

"If I had to describe this in one word: **functional**."

The design system underneath is well-chosen (Syne + Bebas Neue + DM Mono is a sharp, distinctly sport-analytics stack), but the paywall placement and emoji-as-nav-icons undermine what could be a polished product impression.

---

## Inferred Design System

- **Fonts:** Syne (body/UI, 16px base), Bebas Neue (display/headings), DM Mono (monospace/stats), Arial (fallback). 3 families — within the 3-font rule.
- **Colors:**
  - Background: `rgb(5, 10, 12)` — near-black navy, strong dark foundation
  - Body text: `rgb(204, 232, 222)` — mint green, not pure white (correct for dark mode)
  - Gold accent: `rgb(201, 168, 76)` — primary brand color, used on active states and CTAs
  - Teal: `rgb(95, 152, 128)` — secondary accent
  - Bright green: `rgb(53, 217, 103)` — upward movement (transfers in, score up)
  - Dark teal: `rgb(42, 80, 64)` — badge background
- **Heading Scale:** h2 only (no h1 anywhere on site). FIXTURES, GAMEWEEK INFO use Bebas Neue caps — visually strong but semantically incorrect.
- **Spacing Patterns:** Mix of 8px-grid values (8, 16, 24, 28px) and off-grid (13px, 10px).
- **Border Radius:** 6 distinct values (7px, 8px, 10px, 12px, 16px, 20px) — no systematic scale.

---

## Phase 3: Page-by-Page Findings

### Predictions Tab (Homepage)

**Trunk Test: PARTIAL** (4/6)
- ✅ Site identity clear (FPL AI Pro logo top-left)
- ✅ Page identity clear (Predictions tab active with underline)
- ✅ Major sections visible (6 tabs)
- ❌ No h1 — screen readers cannot determine page purpose
- ✅ Local options available (filter buttons: Pts/Form/£/%)
- ❌ No search in primary nav context (it's one of the tabs, not always-visible)

**Issues found:**
- FINDING-001: No h1 on any page
- FINDING-002: Auth buttons (Sign In, Go Pro) are 30px tall — below 44px minimum
- FINDING-003: Filter toggle buttons (£, %) are 33px wide — below 44px minimum
- FINDING-004: Paywall block is the dominant above-the-fold element for free users
- FINDING-007: All 6 nav tabs use emoji icons (AI Slop #7)

### My Squad Tab

**Trunk Test: PARTIAL** (4/6)
- The team import form uses placeholder-as-label (the only guidance disappears when typing)
- Instructions telling users where to find their Team ID are compensating for a UX failure
- Large empty space below the import form (both My Team and sub-tabs show empty state)
- Sub-tabs also use emoji (🧑‍🤝‍🧑, ⚡, 📅) — consistent but wrong

### Fixtures & FDR Tab

**Trunk Test: PASS** (5/6)
- Clean fixture card layout — this is the best-designed tab
- Good use of GW labels on fixture cards
- FDR Heatmap sub-tab label clear
- Only missing: search in context

### Intel Tab

**Trunk Test: PASS** (5/6)
- Trending/Injuries/Price Movers/Best Value sub-tabs clear
- Good use of color-coded position badges (FWD/MID/DEF)
- Number arrows (↑/↓) with green/red semantic color — good
- Emoji in sub-tab labels (🔥, 🏅, 💰, 💎) — consistent problem

### Gameweek Tab

**Trunk Test: FAIL** (3/6)
- Two info cards (GW33, GW34) but massive empty space below
- GW34 countdown timer shows dashes — appears broken or waiting for JS
- No clear primary action for this view — what is the user supposed to do here?
- Page area test fails: can't name the purpose of the empty lower half in 2 seconds

---

## All Findings

### HIGH Impact

**FINDING-001: No h1 on any page**
- All pages lack an h1 element. The heading hierarchy jumps from nothing to h2. Screen readers cannot determine page purpose. SEO suffers.
- Fix: Add a visually hidden (sr-only) h1 to each tab panel, e.g. "Player Predictions", "My Squad", "Fixtures & FDR", etc.
- Files: `frontend/src/components/` (the tab panel components)
- Effort: human ~1 hour / CC ~5 min

**FINDING-002: Auth buttons too small (30px, below 44px minimum)**
- The "Sign In" and "Go Pro" buttons in the top-right header are 30px tall and 77-80px wide. These are the two highest-value CTAs on the site and they fail the 44px minimum touch target rule.
- Fix: Set `.auth-btn { min-height: 44px; padding: 0 16px; }` in the header CSS.
- Affects: every page
- Effort: human ~10 min / CC ~2 min

**FINDING-003: Filter toggle buttons below minimum (33-34px)**
- The filter buttons (£, %, ↻) on the Predictions tab are 33-39px wide. Below the 44px width minimum for touch targets.
- Fix: Add minimum width/height constraints to `.ghost` button class.
- Effort: human ~10 min / CC ~2 min

### MEDIUM Impact

**FINDING-004: Paywall block is the dominant above-the-fold element**
- New free users land on the Predictions tab and the first prominent element they see is a large lock icon with "PRO FEATURE — Upgrade to Pro / Sign Up" text. The Captain Picks section (a major value prop) is completely hidden. This depletes goodwill before the user has seen the product's value.
- Fix: Show a teaser/blur of Captain Picks content with a lighter upgrade prompt, rather than a full opaque paywall block. Alternatively, reorder so free predictions are visible first, captain picks second.
- Effort: human ~2 hours / CC ~20 min

**FINDING-005: Emoji navigation icons (AI Slop #7)**
- All 6 primary nav tabs use emoji as icons: ⚡🏆📅🚨🔍🗓. Secondary sub-tabs also use emoji. Emoji rendering varies across operating systems and looks amateurish at 12px tab font size. This is AI Slop blacklist item #7.
- Fix: Replace with a proper SVG icon library (Lucide, Heroicons, Phosphor) or remove icons entirely — the labels are clear enough without them.
- Files: nav component
- Effort: human ~2 hours / CC ~15 min

**FINDING-006: Non-systematic border radius (6 values)**
- Current values: 7px, 8px, 10px, 12px, 16px, 20px. A design system should use 2-3 values (e.g., sm=4px, md=8px, lg=16px). The 7px value in particular suggests a one-off tweak.
- Fix: Define CSS variables `--radius-sm: 8px`, `--radius-md: 12px`, `--radius-lg: 20px` and standardize.
- Effort: human ~2 hours / CC ~15 min

**FINDING-007: Body line-height: normal (~1.2, should be 1.5)**
- The body element has `line-height: normal`. Browsers compute this as roughly 1.2, significantly below the 1.5x minimum recommended for readability on body text.
- Fix: Set `body { line-height: 1.5; }` in global CSS.
- Effort: human ~5 min / CC ~2 min

**FINDING-008: Nav tab font size 12px**
- Navigation tabs use 12px text. The minimum for body copy is 16px. At 12px with emoji icons, the tabs feel cramped and are harder to read on mobile.
- Fix: Increase to minimum 14px; ideally 15-16px with the emoji removed.
- Effort: human ~5 min / CC ~2 min

**FINDING-009: No color-scheme: dark declaration**
- The site is dark-themed but doesn't declare `color-scheme: dark` on the html element or via a meta tag. Browser UI elements (scrollbars, input fields, select dropdowns) will render in light mode, creating jarring light blobs in the dark interface.
- Fix: Add `<meta name="color-scheme" content="dark">` and `html { color-scheme: dark; }`.
- Effort: human ~5 min / CC ~2 min

**FINDING-010: `transition: all` on player cards**
- Player cards use `transition: all 0.2s`. This animates every CSS property including layout properties (width, height, margin), triggering expensive layout recalculations on hover. Should specify only `transform` and `opacity`.
- Fix: Replace `transition: all` with `transition: transform 0.2s, opacity 0.2s, box-shadow 0.2s`.
- Effort: human ~10 min / CC ~5 min

**FINDING-011: Placeholder-as-label in Squad import (My Squad tab)**
- The team ID input field uses only a placeholder ("e.g. 1234567") with no visible label. When the user starts typing, the guidance disappears. Violates WCAG 1.3.5 and the Design Hard Rules.
- Fix: Add a visible label "FPL Team ID" above the input field.
- Effort: human ~10 min / CC ~5 min

**FINDING-012: Gameweek tab mostly empty / countdown broken**
- The Gameweek tab has two info cards and a large empty region below. The GW34 countdown timer shows dashes, suggesting a JS rendering issue or that the countdown has expired. Empty state with no message or action.
- Fix: (1) Fix or remove broken countdown timer. (2) Add more content to this tab or surface it somewhere more useful.
- Effort: human ~1 hour / CC ~20 min

### POLISH

**FINDING-013: No `font-variant-numeric: tabular-nums` on stat numbers**
- Player scores, ownership percentages, and transfer numbers don't use tabular-nums. Numbers in proportional fonts shift width as values change, causing visual jitter in the player card grid.
- Fix: Add `font-variant-numeric: tabular-nums` to `.card-stat, .stat-value` selectors.
- Effort: human ~10 min / CC ~2 min

**FINDING-014: No skip-navigation link**
- Missing skip-nav link for keyboard users. Without it, keyboard users must tab through the entire nav bar on every page change.
- Fix: Add a `<a href="#main-content" class="sr-only focus:not-sr-only">Skip to content</a>` before the nav.
- Effort: human ~15 min / CC ~5 min

**FINDING-015: Heading text-wrap not set**
- Long headings (especially in Bebas Neue) don't use `text-wrap: balance` or `text-pretty`. On narrow viewports, headings can break awkwardly.
- Fix: Add `h1, h2, h3 { text-wrap: balance; }` to global CSS.
- Effort: human ~5 min / CC ~2 min

---

## Phase 4: Goodwill Reservoir

Starting: 70/100

| Step | Event | Score |
|---|---|---|
| Landing (Predictions) | 70 → 55 | Paywall block is the first prominent element above fold (-15 interstitial) |
| Predictions | 55 → 60 | Player cards are clear and data-rich (+5 saves steps) |
| My Squad | 60 → 55 | Form has instructions compensating for UX failure (-5) |
| Fixtures | 55 → 60 | Clean, no friction (+5 saves steps) |
| Intel | 60 → 65 | Data-dense, well-organized (+5) |
| Gameweek | 65 → 60 | Broken countdown, mostly empty (-5) |

**FINAL: 60/100** — Needs work. The paywall placement is the single biggest drain. Everything else is close to healthy.

---

## Phase 5: Cross-Page Consistency

- Navigation: consistent across all pages ✓
- No footer (fine for an app-like experience)
- Card components: consistently styled across all tabs ✓
- Color usage: consistent (gold = active/CTA, teal = secondary, green = positive movement) ✓
- Emoji usage: consistent but consistently wrong — all tabs and sub-tabs use emoji ✓
- Spacing: mostly consistent with one exception (13px card padding off the 8px grid)
- Tone: consistently utility-focused, good ✓

---

## Phase 6: Quick Wins

These 5 fixes take <30 minutes combined and give the most immediate improvement:

1. **body line-height: 1.5** — one line of CSS, immediate readability improvement everywhere
2. **color-scheme: dark** — two lines, fixes all browser UI elements
3. **Auth buttons min-height: 44px** — five lines of CSS, fixes the two most important CTAs
4. **text-wrap: balance on headings** — one line, prevents awkward heading breaks
5. **font-variant-numeric: tabular-nums on stats** — one line, fixes number jitter in cards

---

## Phase 7: Triage

### Fix in this session
| ID | Finding | Impact | Type |
|---|---|---|---|
| FINDING-001 | No h1 on any page | HIGH | Code |
| FINDING-002 | Auth buttons 30px | HIGH | CSS |
| FINDING-003 | Filter buttons 33px | HIGH | CSS |
| FINDING-007 | Body line-height: normal | MEDIUM | CSS |
| FINDING-008 | Nav tab font 12px | MEDIUM | CSS |
| FINDING-009 | No color-scheme: dark | MEDIUM | CSS |
| FINDING-010 | transition: all on cards | MEDIUM | CSS |
| FINDING-013 | No tabular-nums on stats | POLISH | CSS |
| FINDING-015 | No text-wrap: balance | POLISH | CSS |

### Defer (requires product/content decision)
| ID | Finding | Reason |
|---|---|---|
| FINDING-004 | Paywall placement | Product decision, not a CSS fix |
| FINDING-005 | Emoji nav icons | Requires new SVG icon set |
| FINDING-006 | Non-systematic border radius | Requires design token refactor |
| FINDING-011 | Placeholder-as-label | Requires component changes |
| FINDING-012 | Gameweek empty + countdown | Requires backend data + product decision |
| FINDING-014 | Skip navigation | Requires HTML structure change |

---

## Summary

**Total findings:** 15  
**High impact:** 3  
**Medium impact:** 9  
**Polish:** 3  

**Design Score:** C+ (2.78/4.0 weighted)  
**AI Slop Score:** C — three distinct AI slop instances (emoji as nav icons, emoji in sub-tabs, emoji in section headings)  

**Goodwill: 60/100** — The paywall placement is the single biggest UX debt. Fix it and goodwill jumps to ~75.

**PR summary:** Design audit found 15 issues (3 high, 9 medium, 3 polish). The emoji nav icons, 30px auth buttons, and paywall placement are the critical items. CSS-only quick wins available for 9 of 15 findings.

---

*Generated by /design-review (gstack) on 2026-04-27*
