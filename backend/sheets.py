"""
Google Sheets integration using gspread + a service account.

Sheet column layout (A → T):
  A  name               B  email              C  company
  D  property_address   E  city               F  state
  G  country            H  score              I  tier
  J  population         K  median_income      L  renter_pct
  M  median_rent        N  total_housing_units O  unemployment_rate
  P  email_subject      Q  email_body         R  insights
  S  processed_at       T  status
"""

import os
import logging
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

INPUT_COLUMNS = ["name", "email", "company", "property_address", "city", "state", "country"]
OUTPUT_COLUMNS = [
    "score", "tier", "population", "median_income", "renter_pct",
    "median_rent", "total_housing_units", "unemployment_rate",
    "email_subject", "email_body", "insights", "processed_at", "status",
]
ALL_COLUMNS = INPUT_COLUMNS + OUTPUT_COLUMNS


def _get_sheet():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json"),
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")).sheet1


def ensure_headers():
    """Write the header row if the sheet is empty or missing headers."""
    sheet = _get_sheet()
    existing = sheet.row_values(1)
    if not existing or existing[0].lower() != "name":
        sheet.insert_row(ALL_COLUMNS, 1)
        logger.info("Header row written to sheet.")


def get_all_leads():
    """Return all rows as a list of dicts (including unprocessed ones)."""
    sheet = _get_sheet()
    return sheet.get_all_records()


def get_unprocessed_leads():
    """
    Return (row_number, lead_dict) pairs for rows that have input data
    but no score yet. Row numbers are 1-indexed (row 1 = headers).
    """
    sheet = _get_sheet()
    records = sheet.get_all_records()
    unprocessed = []
    for i, row in enumerate(records):
        has_input = row.get("name") and row.get("city") and row.get("state")
        already_scored = row.get("score")
        if has_input and not already_scored:
            unprocessed.append((i + 2, row))  # +2: 1-indexed + header row
    return unprocessed


def write_enriched_lead(row_num, enriched, score_result, outreach):
    """
    Write enrichment + scoring + outreach results back to the sheet row.
    Only updates OUTPUT_COLUMNS — leaves input columns untouched.
    """
    sheet = _get_sheet()
    headers = sheet.row_values(1)

    updates = {
        "score":               score_result.get("score", ""),
        "tier":                score_result.get("tier", ""),
        "population":          enriched.get("population", ""),
        "median_income":       enriched.get("median_income", ""),
        "renter_pct":          enriched.get("renter_pct", ""),
        "median_rent":         enriched.get("median_rent", ""),
        "total_housing_units": enriched.get("total_housing_units", ""),
        "unemployment_rate":   enriched.get("unemployment_rate", ""),
        "email_subject":       outreach.get("subject", ""),
        "email_body":          outreach.get("body", ""),
        "insights":            " | ".join(outreach.get("insights", [])),
        "processed_at":        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status":              "processed",
    }

    # Batch the cell updates instead of one call per cell
    cell_updates = []
    for col_name, value in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cell_updates.append(gspread.Cell(row_num, col_idx, value))

    if cell_updates:
        sheet.update_cells(cell_updates)
        logger.info(f"Row {row_num} updated in sheet.")
