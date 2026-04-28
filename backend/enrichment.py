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


def _search_wikipedia_title(query):
    """Return the best Wikipedia title for a query, or None if no result is found."""
    if not query:
        return None

    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
            headers={"User-Agent": "EliseAI-LeadIntel/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        titles = resp.json()[1]
        return titles[0] if titles else None
    except Exception as e:
        logger.warning(f"Wikipedia search error for {query}: {e}")
        return None


def get_company_summary(company):
    """Fetch public company context from Wikipedia when a likely page exists."""
    title = _search_wikipedia_title(company)
    if not title:
        return ""

    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
            headers={"User-Agent": "EliseAI-LeadIntel/1.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("type") == "disambiguation":
                return ""
            return data.get("extract", "")[:500]
    except Exception as e:
        logger.warning(f"Wikipedia company summary error for {company}: {e}")
    return ""


def get_rentcast_property_data(lead):
    """Fetch property-level data from RentCast when RENTCAST_API_KEY is configured."""
    api_key = os.getenv("RENTCAST_API_KEY")
    if not api_key:
        return {}

    address_parts = [
        lead.get("property_address", ""),
        lead.get("city", ""),
        lead.get("state", ""),
    ]
    address = ", ".join(part for part in address_parts if part)
    if not address:
        return {}

    try:
        resp = requests.get(
            "https://api.rentcast.io/v1/properties",
            params={"address": address, "limit": 1},
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 401:
            logger.warning("RentCast auth failed — check RENTCAST_API_KEY.")
            return {}
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            records = data.get("properties") or data.get("data") or data.get("results") or []
        else:
            records = data
        if not records:
            logger.info(f"RentCast returned no property match for {address}")
            return {}

        prop = records[0]
        owner = prop.get("owner") or {}
        owner_names = owner.get("names") or owner.get("name") or []
        if isinstance(owner_names, list):
            owner_name = ", ".join(str(name) for name in owner_names[:2])
        else:
            owner_name = str(owner_names)

        result = {
            "rentcast_property_id": prop.get("id", ""),
            "rentcast_property_type": prop.get("propertyType", ""),
            "rentcast_bedrooms": prop.get("bedrooms"),
            "rentcast_bathrooms": prop.get("bathrooms"),
            "rentcast_square_footage": prop.get("squareFootage"),
            "rentcast_lot_size": prop.get("lotSize"),
            "rentcast_year_built": prop.get("yearBuilt"),
            "rentcast_owner_type": owner.get("type", ""),
            "rentcast_owner_name": owner_name,
        }
        logger.info(
            f"RentCast property match for {address}: "
            f"{result.get('rentcast_property_type') or 'unknown type'}"
        )
        return {k: v for k, v in result.items() if v not in (None, "")}
    except Exception as e:
        logger.warning(f"RentCast property lookup error for {address}: {e}")
        return {}


def enrich_lead(lead):
    """
    Full enrichment pipeline for a single lead.
    Returns a dict of enriched fields; any field may be missing if its API call fails.
    """
    city = lead.get("city", "")
    state = lead.get("state", "")
    address = lead.get("property_address", "")
    company = lead.get("company", "")

    result = {}

    # --- RentCast (property-level data) ---
    result.update(get_rentcast_property_data(lead))

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

    # --- Wikipedia (company context) ---
    company_wiki = get_company_summary(company)
    result["company_summary"] = company_wiki

    return result
