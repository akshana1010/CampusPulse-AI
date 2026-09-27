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
    suggested_solution  – practical actionable recommendation for college administration
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

# ── Base Fallback Solutions by Category ──────────────────────────────────────
FALLBACK_SOLUTIONS = {
    "Safety": "Inspect the affected campus area immediately, repair or enhance lighting/security measures, and conduct a safety review with campus security personnel.",
    "Electricity": "Dispatch the electrical maintenance team to inspect faulty wiring, replace damaged components or fixtures, and verify electrical circuit safety.",
    "Water": "Deploy plumbing staff to inspect the water pipeline/facility, isolate and repair leakages, and restore clean drinking/utility water supply.",
    "Internet": "Have the campus IT & networking team test the local access points, reboot/reconfigure routers or switches, and restore stable bandwidth connectivity.",
    "Cleanliness": "Assign custodial and housekeeping staff for thorough sanitization, deploy additional waste bins, and increase scheduled cleaning inspections.",
    "Infrastructure": "Coordinate with the campus estate and civil maintenance department to inspect structural damage and schedule prompt repairs or furniture replacement.",
    "Transport": "Coordinate with the campus transport supervisor to review bus timings, shuttle routes, or parking bay management to resolve congestion.",
    "Academic": "Forward this report to the concerned department head or laboratory coordinator to address classroom equipment and academic facility requirements.",
    "Accessibility": "Inspect pathways and facilities to install or repair ramps, handrails, or assistive infrastructure to ensure universal accessibility compliance.",
    "Other": "Review the reported issue with the campus facilities administration and initiate appropriate maintenance or corrective action.",
}

# ── Fallback result (used when API call fails or key is missing) ───────────────
_FALLBACK = {
    "predicted_category": "Other",
    "priority": "Low",
    "summary": "AI analysis unavailable. Please review manually.",
    "sentiment": "neutral",
    "confidence": 0.0,
    "suggested_solution": FALLBACK_SOLUTIONS["Other"],
    "raw_response": "",
}


def get_fallback_solution(category: str, title: str = "", description: str = "") -> str:
    """
    Generate a smart, practical college-focused solution based on category
    and problem keywords when Gemini is offline or quota is exhausted.
    """
    text = f"{title} {description}".lower()

    # Context-specific fine-tuning
    if "light" in text or "dark" in text:
        return "Inspect the affected area and repair or install adequate LED lighting. Conduct a nighttime safety inspection to ensure proper visibility."
    if "pipe" in text or "leak" in text or "overflow" in text or "flood" in text:
        return "Dispatch plumbing team immediately to isolate the valve, repair the leaking pipeline, and ensure water drainage is cleared."
    if "wifi" in text or "wi-fi" in text or "internet" in text or "signal" in text:
        return "Instruct campus IT networking staff to inspect and reboot the wireless access point, replace faulty network patch cords, and verify signal strength."
    if "wire" in text or "spark" in text or "socket" in text or "switchboard" in text:
        return "Depute qualified campus electricians to isolate power, insulate exposed wiring, and replace faulty electrical switchgear."
    if "dustbin" in text or "garbage" in text or "trash" in text or "smell" in text:
        return "Deploy sanitation crew to clear accumulated waste, sanitize the area, and install covered disposal bins."
    if "bench" in text or "chair" in text or "desk" in text or "window" in text or "door" in text:
        return "Dispatch carpentry and civil maintenance staff to repair or replace the damaged furniture and hardware fixtures."
    if "bus" in text or "shuttle" in text or "parking" in text:
        return "Coordinate with transport staff to adjust vehicle trip schedules and streamline parking bay allocation."
    if "projector" in text or "lab" in text or "computer" in text:
        return "Notify lab technical assistant and department coordinator to service audiovisual/computer hardware before upcoming lectures."

    cat = category if category in FALLBACK_SOLUTIONS else "Other"
    return FALLBACK_SOLUTIONS.get(cat, FALLBACK_SOLUTIONS["Other"])


def analyze_report(title: str, description: str, user_category: str) -> dict:
    """
    Send the report text to Gemini and parse the structured JSON response.

    Args:
        title:          Report title entered by the student.
        description:    Full problem description.
        user_category:  Category the student selected in the form.

    Returns:
        A dict with keys: predicted_category, priority, summary,
                          sentiment, confidence, suggested_solution, raw_response.
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
        result = _parse_response(raw_text, user_category, title, description)
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
  "confidence": <float between 0.0 and 1.0>,
  "suggested_solution": "<1-2 sentence practical, actionable recommendation for college administration to fix or resolve this problem>"
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


def _parse_response(raw_text: str, fallback_category: str, title: str = "", description: str = "") -> dict:
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

    pred_cat = _safe_get(data, "predicted_category", VALID_CATEGORIES, fallback_category)
    solution = data.get("suggested_solution")
    if not solution or not str(solution).strip():
        solution = get_fallback_solution(pred_cat, title, description)

    return {
        "predicted_category": pred_cat,
        "priority": _safe_get(data, "priority", VALID_PRIORITIES, "Low"),
        "summary": str(data.get("summary", _FALLBACK["summary"]))[:500],
        "sentiment": _safe_get(data, "sentiment", VALID_SENTIMENTS, "neutral"),
        "confidence": _clamp_float(data.get("confidence", 0.0)),
        "suggested_solution": str(solution)[:500],
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

    # 6. Practical Suggested Solution
    suggested_solution = get_fallback_solution(predicted_category, title, description)

    return {
        "predicted_category": predicted_category,
        "priority": priority,
        "summary": summary,
        "sentiment": sentiment,
        "confidence": confidence,
        "suggested_solution": suggested_solution,
        "raw_response": json.dumps({
            "source": "local_fallback",
            "predicted_category": predicted_category,
            "priority": priority,
            "summary": summary,
            "sentiment": sentiment,
            "confidence": confidence,
            "suggested_solution": suggested_solution,
        }),
    }
