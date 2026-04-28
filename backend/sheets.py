"""
Google Sheets integration using gspread + a service account.

Sheet column layout:
  A  name               B  email              C  company
  D  property_address   E  city               F  state
  G  country            H  score              I  tier
  J  population         K  median_income      L  renter_pct
  M  median_rent        N  total_housing_units O  unemployment_rate
  P  email_subject      Q  email_body         R  insights
  S  processed_at       T  status
  Additional metadata columns are appended automatically.
"""

import os
import logging
import re
import time
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

INPUT_COLUMNS = ["name", "email", "company", "property_address", "city", "state", "country"]
META_COLUMNS = ["lead_key", "processing_started_at"]
OUTPUT_COLUMNS = [
    "score", "tier", "population", "median_income", "renter_pct",
    "median_rent", "total_housing_units", "unemployment_rate",
    "rentcast_property_id", "rentcast_property_type", "rentcast_bedrooms",
    "rentcast_bathrooms", "rentcast_square_footage", "rentcast_lot_size",
    "rentcast_year_built", "rentcast_owner_type", "rentcast_owner_name",
    "company_summary", "email_subject", "email_body", "insights", "processed_at", "status",
]
ALL_COLUMNS = INPUT_COLUMNS + OUTPUT_COLUMNS + META_COLUMNS
RECORDS_CACHE_SECONDS = 15
PROCESSING_STALE_AFTER_MINUTES = 3

_sheet = None
_headers = None
_records_cache = {"fetched_at": 0, "records": None}


def _lead_identity_key(row):
    """
    Stable dedupe key for a managed property.
    Prefer address + city + state; fall back to company/contact if address is missing.
    """
    parts = [
        row.get("property_address"),
        row.get("city"),
        row.get("state"),
        row.get("country") or "US",
    ]
    if not any(parts[:3]):
        parts = [row.get("company"), row.get("email"), row.get("name")]

    normalized = "|".join(str(p or "").strip().lower() for p in parts)
    return re.sub(r"[^a-z0-9|]+", "", normalized)


def _parse_sheet_datetime(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _get_sheet():
    global _sheet
    if _sheet is not None:
        return _sheet

    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json"),
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)
    _sheet = gc.open_by_key(os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")).sheet1
    return _sheet


def _invalidate_records_cache():
    _records_cache["fetched_at"] = 0
    _records_cache["records"] = None


def _get_headers(force=False):
    global _headers
    if _headers is not None and not force:
        return _headers
    _headers = _get_sheet().row_values(1)
    return _headers


def _get_records(force=False):
    now = time.monotonic()
    if (
        not force
        and _records_cache["records"] is not None
        and now - _records_cache["fetched_at"] < RECORDS_CACHE_SECONDS
    ):
        return [dict(row) for row in _records_cache["records"]]

    records = _get_sheet().get_all_records()
    _records_cache["fetched_at"] = now
    _records_cache["records"] = [dict(row) for row in records]
    return records


def ensure_headers():
    """Write or append required headers without disturbing existing data."""
    sheet = _get_sheet()
    existing = _get_headers(force=True)
    if not existing or existing[0].lower() != "name":
        sheet.insert_row(ALL_COLUMNS, 1)
        _get_headers(force=True)
        _invalidate_records_cache()
        logger.info("Header row written to sheet.")
        return

    missing = [col for col in ALL_COLUMNS if col not in existing]
    if missing:
        start_col = len(existing) + 1
        cells = [
            gspread.Cell(1, start_col + i, col)
            for i, col in enumerate(missing)
        ]
        sheet.update_cells(cells)
        _get_headers(force=True)
        _invalidate_records_cache()
        logger.info(f"Added missing sheet header(s): {', '.join(missing)}")


def get_all_leads():
    """Return all rows as a list of dicts (including unprocessed ones)."""
    records = _get_records()
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=PROCESSING_STALE_AFTER_MINUTES)
    for row in records:
        row["lead_key"] = row.get("lead_key") or _lead_identity_key(row)
        status = str(row.get("status") or "").lower()
        started_at = _parse_sheet_datetime(row.get("processing_started_at"))
        if status == "processing" and not row.get("score") and (not started_at or started_at < stale_cutoff):
            row["status"] = "unprocessed"
    return records


def append_lead(lead):
    """Append a new input lead row using the canonical sheet column layout."""
    sheet = _get_sheet()
    headers = _get_headers()
    lead_key = _lead_identity_key(lead)
    row = {
        **{col: lead.get(col, "") for col in INPUT_COLUMNS},
        "country": lead.get("country") or "US",
        "status": "unprocessed",
        "lead_key": lead_key,
    }
    values = [row.get(header, "") for header in headers]
    sheet.append_row(values, value_input_option="USER_ENTERED")
    _invalidate_records_cache()
    logger.info(f"Appended lead '{lead.get('name')}' to sheet.")
    return row


def get_unprocessed_leads():
    """
    Return (row_number, lead_dict) pairs for rows that have input data
    but no score yet and no already-processed duplicate.
    Row numbers are 1-indexed (row 1 = headers).
    """
    records = _get_records()
    processed_keys = {
        _lead_identity_key(row)
        for row in records
        if row.get("score") and _lead_identity_key(row)
    }
    queued_keys = set()
    skipped = {}
    unprocessed = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=PROCESSING_STALE_AFTER_MINUTES)
    for i, row in enumerate(records):
        has_input = row.get("name") and row.get("city") and row.get("state")
        already_scored = row.get("score")
        status = str(row.get("status") or "").lower()
        key = _lead_identity_key(row)

        started_at = _parse_sheet_datetime(row.get("processing_started_at"))
        stale_processing = status == "processing" and not already_scored and (
            not started_at or started_at < stale_cutoff
        )
        already_handled = already_scored or (
            status in {"processing", "processed", "duplicate", "failed"} and not stale_processing
        )

        if has_input and not already_handled and key not in processed_keys and key not in queued_keys:
            unprocessed.append((i + 2, row))  # +2: 1-indexed + header row
            queued_keys.add(key)
            continue

        reason = None
        if not has_input:
            reason = "missing_input"
        elif already_scored:
            reason = "already_scored"
        elif status:
            reason = f"status_{status}"
        elif key in processed_keys:
            reason = "duplicate_processed_key"
        elif key in queued_keys:
            reason = "duplicate_queued_key"
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1

    if skipped:
        logger.info(f"Skipped lead rows by reason: {skipped}")
    return unprocessed


def copy_duplicate_outputs():
    """
    Fill unscored duplicate property rows with the first processed row's outputs.
    Returns the number of duplicate rows updated.
    """
    sheet = _get_sheet()
    headers = _get_headers()
    records = _get_records()

    processed_by_key = {}
    for row in records:
        key = _lead_identity_key(row)
        if key and row.get("score") and key not in processed_by_key:
            processed_by_key[key] = row

    cell_updates = []
    updated_rows = 0
    for i, row in enumerate(records):
        key = _lead_identity_key(row)
        source = processed_by_key.get(key)
        if not key or not source or row.get("score"):
            continue

        row_num = i + 2
        updated_rows += 1
        for col_name in OUTPUT_COLUMNS + META_COLUMNS:
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                value = _lead_identity_key(row) if col_name == "lead_key" else source.get(col_name, "")
                if col_name == "status":
                    value = "duplicate"
                cell_updates.append(gspread.Cell(row_num, col_idx, value))

    if cell_updates:
        sheet.update_cells(cell_updates)
        _invalidate_records_cache()
        logger.info(f"Copied existing enrichment to {updated_rows} duplicate row(s).")

    return updated_rows


def mark_lead_processing(row_num, lead):
    """Persist in-flight state before expensive enrichment starts."""
    sheet = _get_sheet()
    headers = _get_headers()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    updates = {
        "lead_key": _lead_identity_key(lead),
        "processing_started_at": now,
        "status": "processing",
    }
    cells = [
        gspread.Cell(row_num, headers.index(col_name) + 1, value)
        for col_name, value in updates.items()
        if col_name in headers
    ]
    if cells:
        sheet.update_cells(cells)
        _invalidate_records_cache()
        logger.info(f"Row {row_num} marked as processing.")


def mark_lead_failed(row_num, lead):
    """Persist failure state so the frontend does not retry the same bad row forever."""
    sheet = _get_sheet()
    headers = _get_headers()
    updates = {
        "lead_key": _lead_identity_key(lead),
        "status": "failed",
    }
    cells = [
        gspread.Cell(row_num, headers.index(col_name) + 1, value)
        for col_name, value in updates.items()
        if col_name in headers
    ]
    if cells:
        sheet.update_cells(cells)
        _invalidate_records_cache()
        logger.info(f"Row {row_num} marked as failed.")


def write_enriched_lead(row_num, lead, enriched, score_result, outreach):
    """
    Write enrichment + scoring + outreach results back to the sheet row.
    Only updates OUTPUT_COLUMNS — leaves input columns untouched.
    """
    sheet = _get_sheet()
    headers = _get_headers()

    updates = {
        "score":               score_result.get("score", ""),
        "tier":                score_result.get("tier", ""),
        "population":          enriched.get("population", ""),
        "median_income":       enriched.get("median_income", ""),
        "renter_pct":          enriched.get("renter_pct", ""),
        "median_rent":         enriched.get("median_rent", ""),
        "total_housing_units": enriched.get("total_housing_units", ""),
        "unemployment_rate":   enriched.get("unemployment_rate", ""),
        "rentcast_property_id": enriched.get("rentcast_property_id", ""),
        "rentcast_property_type": enriched.get("rentcast_property_type", ""),
        "rentcast_bedrooms": enriched.get("rentcast_bedrooms", ""),
        "rentcast_bathrooms": enriched.get("rentcast_bathrooms", ""),
        "rentcast_square_footage": enriched.get("rentcast_square_footage", ""),
        "rentcast_lot_size": enriched.get("rentcast_lot_size", ""),
        "rentcast_year_built": enriched.get("rentcast_year_built", ""),
        "rentcast_owner_type": enriched.get("rentcast_owner_type", ""),
        "rentcast_owner_name": enriched.get("rentcast_owner_name", ""),
        "company_summary":      enriched.get("company_summary", ""),
        "email_subject":       outreach.get("subject", ""),
        "email_body":          outreach.get("body", ""),
        "insights":            " | ".join(outreach.get("insights", [])),
        "processed_at":        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status":              "processed",
        "lead_key":            _lead_identity_key(lead),
    }

    # Batch the cell updates instead of one call per cell
    cell_updates = []
    for col_name, value in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cell_updates.append(gspread.Cell(row_num, col_idx, value))

    if cell_updates:
        sheet.update_cells(cell_updates)
        _invalidate_records_cache()
        logger.info(f"Row {row_num} updated in sheet.")
