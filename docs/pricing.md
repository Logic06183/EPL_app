# Pricing

**Decided 2026-10-20 (Craig delegated the call):**

- This season (2026-27) is free. Everyone who signs in before the paywall is a founder and pays half price for life: R225 season pass, R39/month (changed the same day from "free for life", which would have meant no early user ever pays; only 3 accounts existed).
- Paywall on **1 August 2027** (`LAUNCH_FREE_UNTIL=2027-08-01` on `epl-backend`).
- Season pass **R449** once-off, valid to 31 May; monthly **R79**, auto-renewing (`PLANS` in `app/api/payments.py`).
- Free forever: predictions, captain picks, fixtures, track record. Pro: briefing, transfer planner, optimiser, mini-league.

The rest of this page is the reasoning behind that.

## What competitors charge (checked October 2026)

| Product | Price | Notes |
|---|---|---|
| FPL Review | ~$4.50/month (Patreon) | The "solver" crowd's favourite; projections + planner |
| Fantasy Football Scout | ~£3–6/month; annual plans | Content + Opta stats |
| Fantasy Football Hub | £5–8/month on annual plans; £12–15/month monthly in the app | Heavy marketing, frequent 50% off |
| Fantasy Football Fix | Season tickets | Tools + planner |

R199/month is roughly £8.50 — the top of this range, for a product with no
public track record yet. FPL is seasonal (August–May): people buy for a
season, and monthly subscribers churn after their team is "fixed" or once
they've dropped out of their mini-league race.

## Recommendation

1. **Sell a season pass first, monthly second.** e.g. R449/season (~£19)
   and R79/month. Launch the pass in pre-season (July–August 2027), when
   people commit to tools.
2. **What stays free:** predictions, captain picks, fixture difficulty and the
   **track record**. The track record is the sales pitch, so it must be public.
3. **What's paid:** the personal weekly briefing every gameweek, the transfer
   planner (`/plan`), the full squad optimiser, and the 3-GW planner.
4. **Founders:** keep the free-for-life founder perk for this season's
   sign-ups (it's already promised in code), and ask them for testimonials.
5. **International buyers:** PayFast charges in ZAR and mainly serves SA
   cards. Most FPL players are in the UK, Ireland, India, Nigeria and so on.
   Add a GBP/USD checkout (Paddle or Lemon Squeezy act as merchant of record
   and handle VAT) before marketing outside SA.
6. **Decide with data:** `/api/admin/funnel` shows visit → team import →
   briefing → paywall → upgrade click → checkout. Run this season free,
   watch where people drop, then set the price.

## Gating switches (for when the paywall goes on)

During the launch grace period everything is open. To make a feature Pro,
add `require_pro(user)` at the top of its endpoint (a no-op during grace):

| Feature | Endpoint |
|---|---|
| Transfer plan + chips | `plan_transfers` in `app/api/fpl_team.py` |
| Mini-league view | `mini_league` in `app/api/fpl_team.py` |
| Squad optimiser | `optimize_squad` in `app/api/teams.py` |
| Briefing (already metered) | `FREE_BRIEFINGS_PER_GW` env var |

The frontend already shows the upgrade modal on any 403 `upgrade_required`.
