"""
Lead scoring for EliseAI — 4 dimensions, 100 points total.

Assumptions (documented):
  EliseAI sells leasing automation to multifamily property managers.
  A high-value lead manages many units in a market with strong, active rental demand.
  We score on what we can measure from free public data (Census + FRED).

Dimensions:
  1. Market Size       (20 pts) — total housing units in the county
  2. Rental Demand     (20 pts) — % of households that are renter-occupied
  3. Economic Health   (20 pts) — median household income + state unemployment rate
  4. Market Scale      (20 pts) — county population (proxy for lead volume)
  5. Property Fit      (20 pts) — RentCast property type, scale, owner, and vintage

Tiers:
  Hot   80–100
  Warm  60–79
  Cool  40–59
  Pass  <40
"""


def _score_market_size(total_housing_units):
    """More housing units = larger addressable portfolio for EliseAI."""
    u = total_housing_units or 0
    if u > 200_000: return 20
    if u > 100_000: return 17
    if u > 50_000:  return 14
    if u > 20_000:  return 10
    if u > 5_000:   return 6
    return 2


def _score_rental_demand(renter_pct):
    """Higher renter % = more leasing transactions happening = more EliseAI value."""
    p = renter_pct or 0
    if p > 55: return 20
    if p > 50: return 17
    if p > 45: return 14
    if p > 40: return 10
    if p > 35: return 6
    return 2


def _score_economic_health(median_income, unemployment_rate):
    """
    Income proxy: stronger income = premium units, better-quality tenants.
    Unemployment proxy: low unemployment = healthy tenant base, stable operators.
    Split 10 / 10 between income and unemployment.
    """
    income = median_income or 0
    if income > 90_000: income_pts = 10
    elif income > 75_000: income_pts = 8
    elif income > 60_000: income_pts = 6
    elif income > 45_000: income_pts = 4
    else: income_pts = 2

    unemp = unemployment_rate if unemployment_rate is not None else 5.0
    if unemp < 3.0: unemp_pts = 10
    elif unemp < 4.0: unemp_pts = 8
    elif unemp < 5.0: unemp_pts = 6
    elif unemp < 6.5: unemp_pts = 4
    else: unemp_pts = 1

    return income_pts + unemp_pts


def _score_market_scale(population):
    """Larger population = more renters in absolute terms = higher ceiling for EliseAI ROI."""
    p = population or 0
    if p > 2_000_000: return 20
    if p > 1_000_000: return 17
    if p > 500_000:   return 14
    if p > 200_000:   return 10
    if p > 75_000:    return 6
    return 2


def _score_property_fit(enriched):
    """Property-level fit from RentCast. Missing data gets a neutral-ish baseline."""
    if not enriched.get("rentcast_property_id"):
        return 8

    prop_type = str(enriched.get("rentcast_property_type") or "").lower()
    if prop_type in {"apartment", "multi-family", "multifamily"}:
        type_pts = 8
    elif prop_type in {"condo", "townhouse"}:
        type_pts = 5
    elif prop_type:
        type_pts = 2
    else:
        type_pts = 4

    bedrooms = enriched.get("rentcast_bedrooms") or 0
    sqft = enriched.get("rentcast_square_footage") or 0
    if bedrooms >= 20 or sqft >= 20_000:
        scale_pts = 6
    elif bedrooms >= 10 or sqft >= 10_000:
        scale_pts = 4
    elif bedrooms >= 3 or sqft >= 3_000:
        scale_pts = 2
    else:
        scale_pts = 1

    owner_type = str(enriched.get("rentcast_owner_type") or "").lower()
    owner_pts = 3 if owner_type == "organization" else 1

    year_built = enriched.get("rentcast_year_built") or 0
    if year_built >= 2010:
        vintage_pts = 3
    elif year_built >= 1990:
        vintage_pts = 2
    else:
        vintage_pts = 1

    return min(type_pts + scale_pts + owner_pts + vintage_pts, 20)


def score_lead(enriched):
    """
    Score a lead from its enriched data dict.

    Returns:
      {
        "score": int (0–100),
        "tier": str,
        "breakdown": {
          "<key>": {"score": int, "max": int, "label": str}
        }
      }
    """
    market_size   = _score_market_size(enriched.get("total_housing_units"))
    rental_demand = _score_rental_demand(enriched.get("renter_pct"))
    econ_health   = _score_economic_health(
        enriched.get("median_income"),
        enriched.get("unemployment_rate"),
    )
    market_scale  = _score_market_scale(enriched.get("population"))
    property_fit  = _score_property_fit(enriched)

    total = market_size + rental_demand + econ_health + market_scale + property_fit

    if total >= 80:   tier = "Hot"
    elif total >= 60: tier = "Warm"
    elif total >= 40: tier = "Cool"
    else:             tier = "Pass"

    return {
        "score": total,
        "tier": tier,
        "breakdown": {
            "marketSize":     {"score": market_size,   "max": 20, "label": "Market Size"},
            "rentalDemand":   {"score": rental_demand, "max": 20, "label": "Rental Demand"},
            "economicHealth": {"score": econ_health,   "max": 20, "label": "Economic Health"},
            "marketScale":    {"score": market_scale,  "max": 20, "label": "Market Scale"},
            "propertyFit":    {"score": property_fit,  "max": 20, "label": "Property Fit"},
        },
    }
