"""
CampusPulse AI – AI Service
Integrates with the Google Gemini API to analyse campus problem reports.

Uses the current google-genai SDK (google.genai), which replaced the
deprecated google-generativeai (google.generativeai) package.

Returns:
    predicted_category  – one of the CATEGORIES enum values
    priority            – Low | Medium | High | Critical
    summary             – 1-2 sentence human-readable summary
    sentiment           – positive | neutral | negative | urgent
    confidence          – float 0.0–1.0
    raw_response        – full string from the model (for auditing)
"""

import json
import logging
from flask import current_app

logger = logging.getLogger(__name__)

# Categories and priorities must match models.py
VALID_CATEGORIES = [
    "Safety", "Cleanliness", "Infrastructure", "Transport",
    "Electricity", "Water", "Internet", "Academic", "Accessibility", "Other",
]
VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
VALID_SENTIMENTS = ["positive", "neutral", "negative", "urgent"]

# ── Fallback result (used when API call fails or key is missing) ───────────────
_FALLBACK = {
    "predicted_category": "Other",
    "priority": "Low",
    "summary": "AI analysis unavailable. Please review manually.",
    "sentiment": "neutral",
    "confidence": 0.0,
    "raw_response": "",
}


def analyze_report(title: str, description: str, user_category: str) -> dict:
    """
    Send the report text to Gemini and parse the structured JSON response.

    Args:
        title:          Report title entered by the student.
        description:    Full problem description.
        user_category:  Category the student selected in the form.

    Returns:
        A dict with keys: predicted_category, priority, summary,
                          sentiment, confidence, raw_response.
    """
    import os
    api_key = (current_app.config.get("GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")).strip()
    model_name = (current_app.config.get("GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-3.8-flash").strip()

    if not api_key:
        print("[AI] GEMINI_API_KEY not configured. Using local fallback analyzer", flush=True)
        return _local_fallback_analyzer(title, description, user_category)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(title, description, user_category)

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text = response.text.strip()
        result = _parse_response(raw_text, user_category)
        result["raw_response"] = raw_text
        return result

    except Exception as exc:
        print(f"\n[AI] Gemini API unavailable ({type(exc).__name__}: {exc}).\n[AI] Using local fallback analyzer\n", flush=True)
        logger.warning(
            "[AI] Gemini API failed (%s: %s). Falling back to local analyzer.",
            type(exc).__name__,
            exc,
        )
        return _local_fallback_analyzer(title, description, user_category)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _build_prompt(title: str, description: str, user_category: str) -> str:
    """Construct the structured prompt sent to Gemini."""
    categories_list = ", ".join(VALID_CATEGORIES)
    priorities_list = ", ".join(VALID_PRIORITIES)
    sentiments_list = ", ".join(VALID_SENTIMENTS)

    return f"""You are an AI assistant for a college campus problem reporting system.
Analyze the following student-submitted campus problem report and respond ONLY with a valid JSON object.

Report Title: {title}
Report Description: {description}
Student-Selected Category: {user_category}

Respond with ONLY this JSON structure (no markdown, no explanation):
{{
  "predicted_category": "<one of: {categories_list}>",
  "priority": "<one of: {priorities_list}>",
  "summary": "<1-2 sentence objective summary of the problem>",
  "sentiment": "<one of: {sentiments_list}>",
  "confidence": <float between 0.0 and 1.0>
}}

Priority guidelines:
- Critical: immediate safety risk or campus-wide disruption
- High: significant inconvenience affecting many students
- Medium: moderate issue affecting daily routines
- Low: minor inconvenience or cosmetic issue

Sentiment guidelines:
- urgent: emergency or safety-related language
- negative: frustrated or concerned tone
- neutral: factual, matter-of-fact report
- positive: constructive or polite tone despite the problem
"""


def _parse_response(raw_text: str, fallback_category: str) -> dict:
    """
    Parse and validate the JSON response from Gemini.
    Falls back gracefully if the model returns malformed JSON.
    """
    # Strip markdown code fences if present (some models add them despite instruction)
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Gemini returned non-JSON response: {raw_text[:200]}")
        return dict(_FALLBACK)

    return {
        "predicted_category": _safe_get(data, "predicted_category", VALID_CATEGORIES, fallback_category),
        "priority": _safe_get(data, "priority", VALID_PRIORITIES, "Low"),
        "summary": str(data.get("summary", _FALLBACK["summary"]))[:500],
        "sentiment": _safe_get(data, "sentiment", VALID_SENTIMENTS, "neutral"),
        "confidence": _clamp_float(data.get("confidence", 0.0)),
    }


def _safe_get(data: dict, key: str, valid_values: list, default: str) -> str:
    """Return data[key] if it's in valid_values, else default."""
    value = data.get(key, default)
    return value if value in valid_values else default


def _clamp_float(value) -> float:
    """Clamp a value to [0.0, 1.0]."""
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return 0.0


def _local_fallback_analyzer(title: str, description: str, user_category: str) -> dict:
    """
    Local rule-based fallback analyzer that processes problem reports
    when the Gemini API quota is exhausted or unavailable.
    """
    text = f"{title} {description}".lower()

    # 1. Category Classification
    cat_keywords = {
        "Safety": ["danger", "unsafe", "security", "fight", "theft", "harassment", "guard", "emergency", "fire", "violence", "threat", "accident", "injury", "hazard", "shock"],
        "Electricity": ["electricity", "power", "light", "wire", "fan", "bulb", "switch", "voltage", "socket", "blackout", "outage", "spark", "plug"],
        "Water": ["water", "pipe", "leak", "leaking", "flooding", "tap", "washroom", "toilet", "drinking", "sink", "drainage", "drain", "sewage", "flush"],
        "Internet": ["wifi", "wi-fi", "internet", "network", "router", "connection", "lan", "ethernet", "portal", "signal", "bandwidth"],
        "Cleanliness": ["dustbin", "trash", "garbage", "dirty", "smell", "waste", "cleaning", "pest", "rodent", "cockroach", "litter", "hygiene", "sanitation"],
        "Infrastructure": ["bench", "chair", "desk", "ceiling", "wall", "window", "door", "lift", "elevator", "stairs", "crack", "building", "road", "pothole", "roof", "tiles"],
        "Transport": ["bus", "parking", "shuttle", "vehicle", "bike", "car", "transport", "traffic"],
        "Academic": ["lab", "class", "lecture", "professor", "faculty", "exam", "book", "library", "projector", "computer", "course"],
        "Accessibility": ["ramp", "wheelchair", "disability", "disabled", "braille", "handicap"],
    }

    predicted_category = None
    matched_cat = False
    for cat, kws in cat_keywords.items():
        if any(kw in text for kw in kws):
            predicted_category = cat
            matched_cat = True
            break

    if not predicted_category:
        predicted_category = user_category if user_category in VALID_CATEGORIES else "Other"

    # 2. Priority Detection
    critical_kws = ["emergency", "fire", "danger", "hazard", "threat", "severe", "violence", "shock", "collapse", "gas leak"]
    high_kws = ["unsafe", "accident", "harassment", "live wire", "flooding", "spark", "blackout", "urgent", "injury"]
    medium_kws = ["broken", "damaged", "problem", "shortage", "issue", "leaking", "not working", "fault", "dirty", "slow", "smell"]
    low_kws = ["suggestion", "improvement", "request", "minor", "cosmetic", "paint", "feedback"]

    matched_prio = True
    if any(kw in text for kw in critical_kws):
        priority = "Critical"
    elif any(kw in text for kw in high_kws):
        priority = "High"
    elif any(kw in text for kw in medium_kws):
        priority = "Medium"
    elif any(kw in text for kw in low_kws):
        priority = "Low"
    else:
        matched_prio = False
        priority = "Medium" if len(description.strip()) > 30 else "Low"

    # 3. Sentiment Detection
    urgent_kws = ["emergency", "danger", "fire", "injury", "immediate", "hazard", "critical", "shock"]
    neg_kws = ["broken", "bad", "worst", "poor", "failed", "annoying", "dirty", "slow", "frustrated", "terrible", "smelly", "disappointed", "problem", "issue"]
    pos_kws = ["please", "thank", "kindly", "appreciate", "good", "suggest", "help", "hope", "great"]

    if any(kw in text for kw in urgent_kws):
        sentiment = "urgent"
    elif any(kw in text for kw in neg_kws):
        sentiment = "negative"
    elif any(kw in text for kw in pos_kws):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # 4. Confidence
    if matched_cat and matched_prio:
        confidence = 0.85
    elif matched_cat or matched_prio:
        confidence = 0.80
    else:
        confidence = 0.60

    # 5. Objective Summary
    clean_title = title.strip().rstrip(".")
    summary = f"{clean_title}. Issue categorized under {predicted_category} with {priority} priority."

    return {
        "predicted_category": predicted_category,
        "priority": priority,
        "summary": summary,
        "sentiment": sentiment,
        "confidence": confidence,
        "raw_response": json.dumps({
            "source": "local_fallback",
            "predicted_category": predicted_category,
            "priority": priority,
            "summary": summary,
            "sentiment": sentiment,
            "confidence": confidence
        }),
    }
