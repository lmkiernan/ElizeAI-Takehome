import json
import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None

def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


def generate_outreach(lead, enriched, score_result):
    """
    Call Gemini to generate a personalized outreach email and 5 sales insights.

    Returns:
      {
        "subject": str,
        "body": str,
        "insights": [str, str, str, str, str]
      }
    """
    first_name = lead.get("name", "there").split()[0]
    population = enriched.get("population", 0)
    median_income = enriched.get("median_income", 0)
    renter_pct = enriched.get("renter_pct", 0)
    median_rent = enriched.get("median_rent", 0)
    total_units = enriched.get("total_housing_units", 0)
    unemployment = enriched.get("unemployment_rate")
    wiki = enriched.get("wikipedia_summary", "")[:400]

    prompt = f"""You are an SDR at EliseAI, an AI-powered leasing automation platform built for multifamily property managers.

EliseAI's core value props (use these naturally, don't list them all):
- Automates leasing conversations — inquiries, tour scheduling, follow-ups
- 60-second response time vs. industry average of 4+ hours
- Saves leasing agents 20+ hours per week
- Captures after-hours leads that would otherwise go unanswered
- Works across SMS, email, and chat

Your job: generate a personalized outreach email and 5 sales rep insights for this lead.

LEAD:
- Name: {lead.get("name")}
- Company: {lead.get("company")}
- Property: {lead.get("property_address", "")}, {lead.get("city")}, {lead.get("state")}

ENRICHED MARKET DATA ({lead.get("city")}, {lead.get("state")} — county level):
- Population: {population:,}
- Median Household Income: ${median_income:,}
- Renter-Occupied: {renter_pct}% of households
- Median Monthly Rent: ${median_rent:,}
- Total Housing Units: {total_units:,}
- State Unemployment: {f"{unemployment}%" if unemployment else "N/A"}

CITY CONTEXT (Wikipedia):
{wiki if wiki else "No additional context available."}

LEAD SCORE: {score_result["score"]}/100 — Tier: {score_result["tier"]}

Return ONLY valid JSON, no markdown, no extra text:
{{
  "subject": "subject line here",
  "body": "full email body (use \\n for newlines)",
  "insights": ["insight 1", "insight 2", "insight 3", "insight 4", "insight 5"]
}}

EMAIL RULES:
- Address {first_name} by first name
- Reference 2–3 specific data points from the market data above (naturally, not as a data dump)
- 150–200 words max for the body
- Conversational tone — no buzzwords, no corporate speak
- Single clear CTA: offer a 20-minute call this week
- Sign off as "[Your Name] | EliseAI"

INSIGHTS RULES (for the sales rep, not the prospect):
- Each insight should be specific and reference actual numbers from the enriched data
- Flag whether this is a strong/weak fit and WHY based on the data
- Note anything that makes this market or company especially interesting or concerning
- Keep each insight to 1–2 sentences"""

    try:
        response = _get_model().generate_content(prompt)
        text = response.text.strip()

        # Strip markdown code fences if Gemini wraps the JSON in them
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        return _fallback_outreach(lead, enriched, score_result)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _fallback_outreach(lead, enriched, score_result)


def _fallback_outreach(lead, enriched, score_result):
    """Plain-text fallback if the Gemini call fails."""
    first_name = lead.get("name", "there").split()[0]
    city = lead.get("city", "your market")
    company = lead.get("company", "your team")
    renter_pct = enriched.get("renter_pct")
    renter_line = (
        f"With {renter_pct}% of households in {city} renting, "
        if renter_pct
        else f"With leasing volume in {city} as active as it is, "
    )

    return {
        "subject": f"Automating Leasing at {company} — Quick Question",
        "body": (
            f"Hi {first_name},\n\n"
            f"I came across {company} and wanted to reach out. "
            f"{renter_line}"
            f"I thought EliseAI's leasing automation platform might be worth 20 minutes of your time.\n\n"
            f"We help multifamily teams automate resident communications — "
            f"inquiries, tour scheduling, and follow-ups — so nothing falls through the cracks.\n\n"
            f"Would a quick call this week make sense?\n\n"
            f"Best,\n[Your Name] | EliseAI"
        ),
        "insights": [
            f"Score: {score_result['score']}/100 ({score_result['tier']}) — Gemini API unavailable, manual review recommended.",
            f"Market: {city}, {lead.get('state', '')} — {renter_pct}% renter-occupied" if renter_pct else f"Market: {city}, {lead.get('state', '')}",
            "Verify company size and portfolio count before outreach.",
            "Consider researching recent local multifamily news for personalization.",
            "Fallback email used — regenerate once Gemini API is available.",
        ],
    }
