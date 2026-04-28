import logging

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from enrichment import enrich_lead
from outreach import generate_outreach
from scoring import score_lead
from sheets import (
    append_lead,
    copy_duplicate_outputs,
    ensure_headers,
    get_all_leads,
    get_unprocessed_leads,
    mark_lead_failed,
    mark_lead_processing,
    write_enriched_lead,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _run_pipeline(lead, row_num=None):
    """
    Enrich → score → generate outreach → (optionally) write back to sheet.
    Returns the full result dict, or None on failure.
    """
    try:
        if row_num:
            mark_lead_processing(row_num, lead)
        logger.info(f"Pipeline started for '{lead.get('name')}' in {lead.get('city')}, {lead.get('state')}")
        enriched     = enrich_lead(lead)
        logger.info(f"Enrichment complete for '{lead.get('name')}'")
        score_result = score_lead(enriched)
        logger.info(f"Scoring complete for '{lead.get('name')}': {score_result['score']} ({score_result['tier']})")
        outreach     = generate_outreach(lead, enriched, score_result)
        logger.info(f"Outreach generated for '{lead.get('name')}'")

        if row_num:
            write_enriched_lead(row_num, lead, enriched, score_result, outreach)
            logger.info(f"Pipeline results written for '{lead.get('name')}' to row {row_num}")

        return {
            **lead,
            **enriched,
            "score":         score_result["score"],
            "tier":          score_result["tier"],
            "scoreBreakdown": score_result["breakdown"],
            "emailDraft":    outreach,
            "insights":      outreach.get("insights", []),
            "status":        "processed",
        }
    except Exception as e:
        logger.error(f"Pipeline failed for '{lead.get('name')}': {e}", exc_info=True)
        if row_num:
            mark_lead_failed(row_num, lead)
        return None


# ---------------------------------------------------------------------------
# Scheduled job — runs daily at 9 AM
# ---------------------------------------------------------------------------

def _daily_process_job():
    logger.info("Daily job: checking for unprocessed leads...")
    try:
        copy_duplicate_outputs()
        unprocessed = get_unprocessed_leads()
        logger.info(f"Found {len(unprocessed)} unprocessed lead(s).")
        for row_num, lead in unprocessed:
            _run_pipeline(lead, row_num)
        copy_duplicate_outputs()
    except Exception as e:
        logger.error(f"Daily job error: {e}", exc_info=True)


scheduler = BackgroundScheduler(timezone="America/New_York")
scheduler.add_job(_daily_process_job, "cron", hour=9, minute=0, id="daily_process")
scheduler.start()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


def _to_num(val):
    try:
        return float(val) if val not in (None, "", "N/A") else None
    except (ValueError, TypeError):
        return None


@app.get("/api/leads")
def get_leads():
    """Return all leads from the sheet, normalized for the frontend."""
    try:
        raw_leads = get_all_leads()
        leads = []
        for lead in raw_leads:
            # Re-derive scoreBreakdown from stored enriched values so the
            # frontend can render the breakdown chart for sheet-loaded leads.
            if lead.get("score"):
                enriched_subset = {
                    "population":          _to_num(lead.get("population")),
                    "median_income":       _to_num(lead.get("median_income")),
                    "renter_pct":          _to_num(lead.get("renter_pct")),
                    "total_housing_units": _to_num(lead.get("total_housing_units")),
                    "unemployment_rate":   _to_num(lead.get("unemployment_rate")),
                    "rentcast_property_id": lead.get("rentcast_property_id"),
                    "rentcast_property_type": lead.get("rentcast_property_type"),
                    "rentcast_bedrooms": _to_num(lead.get("rentcast_bedrooms")),
                    "rentcast_square_footage": _to_num(lead.get("rentcast_square_footage")),
                    "rentcast_year_built": _to_num(lead.get("rentcast_year_built")),
                    "rentcast_owner_type": lead.get("rentcast_owner_type"),
                }
                lead["scoreBreakdown"] = score_lead(enriched_subset)["breakdown"]

            # Parse pipe-delimited insights string back into a list
            if isinstance(lead.get("insights"), str):
                lead["insights"] = [s.strip() for s in lead["insights"].split("|") if s.strip()]

            # Restructure flat email columns into the emailDraft object
            lead["emailDraft"] = {
                "subject": lead.pop("email_subject", ""),
                "body":    lead.pop("email_body", ""),
            }

            leads.append(lead)
        return jsonify({"leads": leads})
    except Exception as e:
        logger.error(f"/api/leads error: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/leads")
def create_lead():
    """Append a new lead to the Google Sheet. Frontend auto-processing handles it after insert."""
    lead = request.get_json()
    if not lead or not lead.get("name") or not lead.get("city") or not lead.get("state"):
        return jsonify({"error": "name, city, and state are required"}), 400

    try:
        created = append_lead(lead)
        return jsonify(created), 201
    except Exception as e:
        logger.error(f"/api/leads append error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.post("/api/process")
def process_single():
    """
    Manually trigger the pipeline for a single lead.
    Body: { name, email, company, property_address, city, state, country }
    """
    lead = request.get_json()
    if not lead or not lead.get("name") or not lead.get("city"):
        return jsonify({"error": "name and city are required"}), 400

    logger.info(f"Manual process request received for '{lead.get('name')}'")
    result = _run_pipeline(lead)
    if result:
        return jsonify(result)
    return jsonify({"error": "Pipeline failed — check server logs"}), 500


@app.post("/api/process-all")
def process_all():
    """Re-process every unscored lead in the sheet. Can be called manually from the UI."""
    try:
        copied_before = copy_duplicate_outputs()
        unprocessed = get_unprocessed_leads()
        logger.info(f"Manual process-all request received: {len(unprocessed)} unprocessed lead(s)")
        results = []
        for row_num, lead in unprocessed:
            result = _run_pipeline(lead, row_num)
            if result:
                results.append(result)
        copied_after = copy_duplicate_outputs()
        return jsonify({
            "processed": len(results),
            "duplicatesUpdated": copied_before + copied_after,
            "leads": results,
        })
    except Exception as e:
        logger.error(f"/api/process-all error: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/webhook")
def webhook():
    """
    Called by Google Apps Script whenever a new row is added to the sheet.
    Body: { row: int, name, email, company, property_address, city, state, country }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Empty payload"}), 400

    row_num = data.pop("row", None)
    logger.info(f"Webhook received for '{data.get('name')}' (sheet row {row_num})")

    result = _run_pipeline(data, row_num)
    if result:
        return jsonify({"status": "processed", "score": result["score"], "tier": result["tier"]})
    return jsonify({"status": "failed"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ensure_headers()
    app.run(debug=True, port=5000, use_reloader=False)  # use_reloader=False avoids double-starting APScheduler
