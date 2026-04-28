# EliseAI Lead Intelligence

GTM engineering take-home project that enriches inbound multifamily leads, scores them, generates sales insights, and drafts personalized outreach.

## Overview

Inbound leads start with basic information:

- name
- email
- company
- property_address
- city
- state
- country

The app appends new leads to Google Sheets, enriches them with public APIs, scores them, generates a sales-ready email draft, and writes the outputs back to the Sheet. The frontend displays leads in a Hot/Warm/Cool/Pass dashboard with score breakdowns, market data, property data when available, insights, and editable email copy.

## Tech Stack

- Backend: Flask
- Frontend: React + Vite + Tailwind
- Storage/source of truth: Google Sheets
- AI generation: Gemini
- Scheduling: APScheduler

## Public APIs Used

### U.S. Census Geocoder

Used to map a property address to state/county FIPS codes.

### U.S. Census ACS API

Used for county-level market data:

- population
- median household income
- renter-occupied percentage
- median rent
- total housing units

### FRED

Used for state-level unemployment as a current economic-health signal.

### Wikipedia

Used for city context and best-effort company context.

### RentCast, Optional

If `RENTCAST_API_KEY` is configured, the backend also looks up property-level data by address:

- property type
- bedrooms
- bathrooms
- square footage
- lot size
- year built
- owner type/name

If no RentCast key is provided, the pipeline still works and uses a neutral fallback property-fit score.

## Scoring Model

The lead score is out of 100 points across five dimensions:

- Market Size, 20 pts: total county housing units
- Rental Demand, 20 pts: renter-occupied percentage
- Economic Health, 20 pts: median income and unemployment
- Market Scale, 20 pts: county population
- Property Fit, 20 pts: RentCast property-level fit when available, otherwise a fallback baseline

Tiers:

- Hot: 80-100
- Warm: 60-79
- Cool: 40-59
- Pass: below 40

The model assumes EliseAI’s best leads are multifamily operators in large, renter-heavy, economically healthy markets. Without property-level data, two properties in the same county may score similarly. RentCast improves specificity when configured.

## Workflow

1. User submits a lead from the frontend.
2. Backend appends the row to Google Sheets.
3. Frontend triggers the `process-all` pipeline.
4. Backend marks eligible rows as `processing`.
5. Backend enriches the lead with public APIs.
6. Backend scores the lead.
7. Gemini generates an outreach email and rep-facing sales insights.
8. Backend writes outputs back to Google Sheets.
9. Frontend displays the enriched/scored lead in the dashboard.

Rows are deduplicated with a stable `lead_key` based on property address, city, state, and country. This prevents the same property from being repeatedly processed.

## Google Sheet Columns

Input columns:

- name
- email
- company
- property_address
- city
- state
- country

Output/metadata columns are appended automatically by the backend if missing, including:

- score
- tier
- population
- median_income
- renter_pct
- median_rent
- total_housing_units
- unemployment_rate
- RentCast fields
- company_summary
- email_subject
- email_body
- insights
- processed_at
- status
- lead_key
- processing_started_at

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```bash
GOOGLE_SERVICE_ACCOUNT_PATH=service_account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_sheet_id
GEMINI_API_KEY=your_gemini_key

# Optional
CENSUS_API_KEY=your_census_key
FRED_API_KEY=your_fred_key
RENTCAST_API_KEY=your_rentcast_key
```

The Google service account JSON file should be available at the path configured by `GOOGLE_SERVICE_ACCOUNT_PATH`. Share the Google Sheet with the service account email.

Run backend:

```bash
cd backend
source venv/bin/activate
python app.py
```

Backend runs on:

```text
http://127.0.0.1:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

The Vite proxy forwards `/api` requests to `http://127.0.0.1:5000`.

## Important Routes

```text
GET  /api/health
GET  /api/leads
POST /api/leads
POST /api/process
POST /api/process-all
POST /api/webhook
```

`POST /api/leads` appends a new lead to Google Sheets.

`POST /api/process-all` processes all eligible unprocessed Sheet rows.

`POST /api/webhook` is intended for Google Apps Script automation when new Sheet rows are added.

## Automation

The pipeline can run through:

- frontend form submission
- Process All button
- scheduled backend job at 9 AM America/New_York
- Google Apps Script webhook, if installed/configured

## Google Apps Script

`backend/apps_script.js` contains an optional Apps Script trigger. To use it:

1. Open the Google Sheet.
2. Go to Extensions -> Apps Script.
3. Paste the script.
4. Set `BACKEND_URL` to your public backend URL, such as an ngrok URL ending in `/api/webhook`.
5. Run `installTrigger()` once.
6. Grant permissions.

For local development, the frontend form and Process All button are usually simpler.

## Reliability Notes

- Rows are marked as `processing`, `processed`, `duplicate`, `failed`, or `unprocessed`.
- Stale `processing` rows are treated as unprocessed after a few minutes.
- Google Sheets reads are cached briefly to avoid quota issues.
- RentCast is optional and fails open.
- Gemini has a fallback email/insight generator if the API call fails.

## Rollout Plan

1. Test with sample leads and validate the Sheet pipeline.
2. Review scoring and generated emails with SDRs and sales managers.
3. Pilot with a small SDR group for one to two weeks.
4. Track time saved, reply rate, meeting rate, and email edit rate.
5. Tune scoring thresholds and prompts based on feedback.
6. Roll out to the broader inbound SDR team with documentation and training.
7. Longer term, integrate with CRM and add analytics on which score dimensions predict conversion.

## Demo Talk Track

This project automates the top-of-funnel research loop for inbound multifamily leads. It turns a basic lead row into a scored, enriched, outreach-ready opportunity. The MVP uses free public APIs for market data and optional RentCast property data for more specificity. It does not replace the SDR; it gives the rep prioritization, talking points, and a strong first draft faster.
