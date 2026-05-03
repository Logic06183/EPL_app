"""
Gemini AI service for short, opinionated FPL briefing reasons.

Defensive by design: if the API key is missing, the SDK isn't installed, or the
call fails for any reason, callers get an empty dict back and the briefing
endpoint degrades gracefully to data-only mode. Never raises.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Model + sampling config — tuned for short, factual sentences.
# 2.5 Flash is the cheapest capable Gemini model and supports strict JSON output.
# It's a "thinking" model — internal reasoning eats max_output_tokens before the
# visible answer is generated. For structured JSON tasks like this we disable
# thinking (thinking_budget=0) and give a comfortable token cap so the JSON
# never gets truncated mid-string.
_MODEL = "gemini-2.5-flash"
_TEMPERATURE = 0.3
_MAX_OUTPUT_TOKENS = 1500
_THINKING_BUDGET = 0
_TIMEOUT_S = 8.0


def _api_key() -> Optional[str]:
    """Either GOOGLE_API_KEY (Cloud Run default) or GEMINI_API_KEY."""
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or None


@lru_cache()
def _client():
    """Lazily build a single google-genai Client. Returns None if unavailable."""
    key = _api_key()
    if not key:
        logger.info("Gemini disabled: no GOOGLE_API_KEY / GEMINI_API_KEY set")
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except ImportError:
        logger.warning("google-genai not installed — briefing reasons disabled")
        return None
    except Exception as e:
        logger.warning(f"Gemini client init failed: {e}")
        return None


def is_available() -> bool:
    return _client() is not None


def generate_briefing_reasons(
    *,
    team_name: str,
    alerts: List[Dict[str, Any]],
    captain: Optional[Dict[str, Any]],
    transfer: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ask Gemini for short, plain-English reasons for the structured briefing data.

    Returns:
        {
          "summary":         "1-sentence top-line for the manager (e.g. 'Two doubts...')",
          "captain_reason":  "1 sentence" | "",
          "transfer_reason": "1 sentence" | "",
          "alert_reasons":   { "<player_id>": "1 sentence", ... }
        }
    Empty strings on failure — callers should treat those as 'omit row'.
    """
    fallback: Dict[str, Any] = {
        "summary": "",
        "captain_reason": "",
        "transfer_reason": "",
        "alert_reasons": {},
    }
    client = _client()
    if client is None:
        return fallback

    prompt = _build_prompt(team_name, alerts, captain, transfer)

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=_TEMPERATURE,
                max_output_tokens=_MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_budget=_THINKING_BUDGET),
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return fallback
        data = json.loads(text)
        return {
            "summary":         str(data.get("summary", "") or "")[:240],
            "captain_reason":  str(data.get("captain_reason", "") or "")[:200],
            "transfer_reason": str(data.get("transfer_reason", "") or "")[:200],
            "alert_reasons":   {
                str(k): str(v or "")[:200]
                for k, v in (data.get("alert_reasons") or {}).items()
            },
        }
    except json.JSONDecodeError as e:
        logger.warning(f"Gemini returned non-JSON: {e}")
        return fallback
    except Exception as e:
        logger.warning(f"Gemini generation failed: {e}")
        return fallback


def _build_prompt(
    team_name: str,
    alerts: List[Dict[str, Any]],
    captain: Optional[Dict[str, Any]],
    transfer: Optional[Dict[str, Any]],
) -> str:
    """
    Compact JSON-in/JSON-out prompt. Keeps tokens low (~600 input / ~150 output)
    so the per-call cost is ~$0.0001 even on 2.5 Flash.

    Prompt design notes:
    - The model's failure mode is to *paraphrase* the input — we explicitly
      forbid this and show good/bad examples so it adds insight instead.
    - For each reason type we name the comparative angle (vs current captain,
      vs the player being sold) so the model has a concrete frame.
    - Empty string is a valid output when there's nothing useful to add —
      better than filler.
    """
    payload = {
        "team_name": team_name,
        "alerts":    alerts,
        "captain":   captain,
        "transfer":  transfer,
    }
    return f"""You are a sharp Fantasy Premier League advisor writing for a manager.
British football tone. No emojis, no exclamation marks, no filler.

DATA:
{json.dumps(payload, ensure_ascii=False)}

WRITE THESE REASONS — every reason must add INSIGHT, not paraphrase the input.

GOLDEN RULE: never just restate fields. If you can only restate, use "" (empty).

EXAMPLES:
  alert news: "Knock - 75% chance of playing"
    BAD  reason: "He has a knock and a 75% chance of playing."   (just paraphrasing)
    GOOD reason: "75% fit — playable but consider a safer bench option."

  captain pick: Bowen 5.2 pts, current captain Salah 4.8 pts
    BAD  reason: "Bowen is predicted to score 5.2 points."        (just restating)
    GOOD reason: "Bowen edges Salah by 0.4 — close call, stick if you trust the eye test."

  transfer: Maddison (4.0 form) → Bruno G. (7.2 form), +4.4 improvement
    BAD  reason: "This transfer improves predicted points by 4.4."  (just restating)
    GOOD reason: "Bruno G. on hot form (7.2 vs 4.0) and Maddison's minutes are slipping."

OUTPUT: ONE valid JSON object with these exact keys (omit any reason as ""):
- "summary":         one sentence (<=22 words) capturing the manager's most
                     important decision today. Lead with action ("Watch Bruno's
                     fitness, captain Bowen, consider the Maddison swap.").
                     If everything is settled, say so plainly.
- "captain_reason":  one sentence (<=22 words). Reference form differential,
                     fixture, or comparison with the current captain.
- "transfer_reason": one sentence (<=22 words). Reference form trend or
                     ownership/value, NOT the predicted-points delta directly.
- "alert_reasons":   object mapping each alert's player_id (as string) to a
                     one-sentence reason about *what to do* (bench? captain?
                     hold?), not a paraphrase of the news. Skip a key entirely
                     if you can't add value.

JSON only — no preamble, no markdown."""
