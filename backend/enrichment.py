import os
import requests
import logging

logger = logging.getLogger(__name__)

# Maps state abbreviations to FRED unemployment series IDs (state-level, seasonally adjusted)
FRED_UNEMPLOYMENT_SERIES = {
    "AL": "ALUR", "AK": "AKUR", "AZ": "AZUR", "AR": "ARUR",
    "CA": "CAUR", "CO": "COUR", "CT": "CTUR", "DE": "DEUR",
    "FL": "FLUR", "GA": "GAUR", "HI": "HIUR", "ID": "IDUR",
    "IL": "ILUR", "IN": "INUR", "IA": "IAUR", "KS": "KSUR",
    "KY": "KYUR", "LA": "LAUR", "ME": "MEUR", "MD": "MDUR",
    "MA": "MAUR", "MI": "MIUR", "MN": "MNUR", "MS": "MSUR",
    "MO": "MOUR", "MT": "MTUR", "NE": "NEUR", "NV": "NVUR",
    "NH": "NHUR", "NJ": "NJUR", "NM": "NMUR", "NY": "NYUR",
    "NC": "NCUR", "ND": "NDUR", "OH": "OHUR", "OK": "OKUR",
    "OR": "ORUR", "PA": "PAUR", "RI": "RIUR", "SC": "SCUR",
    "SD": "SDUR", "TN": "TNUR", "TX": "TXUR", "UT": "UTUR",
    "VT": "VTUR", "VA": "VAUR", "WA": "WAUR", "WV": "WVUR",
    "WI": "WIUR", "WY": "WYUR", "DC": "DCUR",
}


def geocode_address(property_address, city, state):
    """Use Census Geocoder to get state + county FIPS codes from a street address."""
    full_address = f"{property_address}, {city}, {state}"
    try:
        resp = requests.get(
            "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress",
            params={
                "address": full_address,
                "benchmark": "Public_AR_Current",
                "vintage": "Census2020_Current",
                "format": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        matches = resp.json().get("result", {}).get("addressMatches", [])
        if not matches:
            logger.warning(f"No geocoder match for: {full_address}")
            return None, None
        counties = matches[0].get("geographies", {}).get("Counties", [])
        if not counties:
            return None, None
        return counties[0]["STATE"], counties[0]["COUNTY"]
    except Exception as e:
        logger.error(f"Geocoder error: {e}")
        return None, None


def get_census_data(state_fips, county_fips):
    """
    Pull ACS 5-year estimates at the county level.

    Variables:
      B01003_001E  Total population
      B19013_001E  Median household income
      B25001_001E  Total housing units
      B25003_001E  Occupied housing units
      B25003_002E  Renter-occupied units
      B25064_001E  Median gross rent
    """
    variables = ",".join([
        "NAME",
        "B01003_001E",
        "B19013_001E",
        "B25001_001E",
        "B25003_001E",
        "B25003_002E",
        "B25064_001E",
    ])
    params = {
        "get": variables,
        "for": f"county:{county_fips}",
        "in": f"state:{state_fips}",
    }
    census_key = os.getenv("CENSUS_API_KEY")
    if census_key:
        params["key"] = census_key

    try:
        resp = requests.get(
            "https://api.census.gov/data/2022/acs/acs5",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if len(rows) < 2:
            return {}
        raw = dict(zip(rows[0], rows[1]))

        total_occupied = int(raw.get("B25003_001E") or 0)
        renter_units = int(raw.get("B25003_002E") or 0)
        renter_pct = round(renter_units / total_occupied * 100, 1) if total_occupied else 0

        return {
            "population": int(raw.get("B01003_001E") or 0),
            "median_income": int(raw.get("B19013_001E") or 0),
            "total_housing_units": int(raw.get("B25001_001E") or 0),
            "renter_pct": renter_pct,
            "median_rent": int(raw.get("B25064_001E") or 0),
            "county_name": raw.get("NAME", ""),
        }
    except Exception as e:
        logger.error(f"Census ACS error: {e}")
        return {}


def get_unemployment_rate(state):
    """Fetch the latest state-level unemployment rate from FRED (free, no key required for basic use)."""
    series_id = FRED_UNEMPLOYMENT_SERIES.get(state.upper())
    if not series_id:
        return None

    params = {
        "series_id": series_id,
        "sort_order": "desc",
        "limit": 1,
        "file_type": "json",
    }
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        params["api_key"] = fred_key

    try:
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
        if not observations:
            return None
        value = observations[0].get("value", ".")
        return float(value) if value != "." else None
    except Exception as e:
        logger.error(f"FRED error for {state}: {e}")
        return None


def get_wikipedia_summary(city, state):
    """Fetch a short city summary from Wikipedia for email personalization context."""
    # Try "{City, State}" format first, then just the city name
    for title in [f"{city},_{state}", city]:
        title_encoded = title.replace(" ", "_")
        try:
            resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_encoded}",
                headers={"User-Agent": "EliseAI-LeadIntel/1.0"},
                timeout=5,
            )
            if resp.status_code == 200:
                extract = resp.json().get("extract", "")
                # Keep first ~400 chars — enough context for email personalization
                return extract[:400]
        except Exception as e:
            logger.warning(f"Wikipedia error for {title}: {e}")
    return ""


def enrich_lead(lead):
    """
    Full enrichment pipeline for a single lead.
    Returns a dict of enriched fields; any field may be missing if its API call fails.
    """
    city = lead.get("city", "")
    state = lead.get("state", "")
    address = lead.get("property_address", "")

    result = {}

    # --- Census (geocoder → ACS) ---
    state_fips, county_fips = geocode_address(address, city, state)
    if state_fips and county_fips:
        census = get_census_data(state_fips, county_fips)
        result.update(census)
        logger.info(f"Census data fetched for {city}, {state}: pop={census.get('population')}")
    else:
        logger.warning(f"Skipping Census for {city}, {state} — geocoder returned no match")

    # --- FRED (state unemployment) ---
    unemp = get_unemployment_rate(state)
    if unemp is not None:
        result["unemployment_rate"] = unemp
        logger.info(f"FRED unemployment for {state}: {unemp}%")

    # --- Wikipedia (city context) ---
    wiki = get_wikipedia_summary(city, state)
    result["wikipedia_summary"] = wiki

    return result
