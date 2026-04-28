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
    ensure_headers,
    get_all_leads,
    get_unprocessed_leads,
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
        enriched     = enrich_lead(lead)
        score_result = score_lead(enriched)
        outreach     = generate_outreach(lead, enriched, score_result)

        if row_num:
            write_enriched_lead(row_num, enriched, score_result, outreach)

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
        return None


# ---------------------------------------------------------------------------
# Scheduled job — runs daily at 9 AM
# ---------------------------------------------------------------------------

def _daily_process_job():
    logger.info("Daily job: checking for unprocessed leads...")
    try:
        unprocessed = get_unprocessed_leads()
        logger.info(f"Found {len(unprocessed)} unprocessed lead(s).")
        for row_num, lead in unprocessed:
            _run_pipeline(lead, row_num)
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


@app.get("/api/leads")
def get_leads():
    """Return all leads from the sheet (processed and unprocessed)."""
    try:
        leads = get_all_leads()
        return jsonify({"leads": leads})
    except Exception as e:
        logger.error(f"/api/leads error: {e}")
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

    result = _run_pipeline(lead)
    if result:
        return jsonify(result)
    return jsonify({"error": "Pipeline failed — check server logs"}), 500


@app.post("/api/process-all")
def process_all():
    """Re-process every unscored lead in the sheet. Can be called manually from the UI."""
    try:
        unprocessed = get_unprocessed_leads()
        results = []
        for row_num, lead in unprocessed:
            result = _run_pipeline(lead, row_num)
            if result:
                results.append(result)
        return jsonify({"processed": len(results), "leads": results})
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
