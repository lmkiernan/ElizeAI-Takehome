"""
Lead scoring for EliseAI — 4 dimensions, 100 points total.

Assumptions (documented):
  EliseAI sells leasing automation to multifamily property managers.
  A high-value lead manages many units in a market with strong, active rental demand.
  We score on what we can measure from free public data (Census + FRED).

Dimensions:
  1. Market Size       (25 pts) — total housing units in the county
  2. Rental Demand     (25 pts) — % of households that are renter-occupied
  3. Economic Health   (25 pts) — median household income + state unemployment rate
  4. Market Scale      (25 pts) — county population (proxy for lead volume)

Tiers:
  Hot   80–100
  Warm  60–79
  Cool  40–59
  Pass  <40
"""


def _score_market_size(total_housing_units):
    """More housing units = larger addressable portfolio for EliseAI."""
    u = total_housing_units or 0
    if u > 200_000: return 25
    if u > 100_000: return 21
    if u > 50_000:  return 17
    if u > 20_000:  return 12
    if u > 5_000:   return 7
    return 3


def _score_rental_demand(renter_pct):
    """Higher renter % = more leasing transactions happening = more EliseAI value."""
    p = renter_pct or 0
    if p > 55: return 25
    if p > 50: return 21
    if p > 45: return 17
    if p > 40: return 12
    if p > 35: return 7
    return 3


def _score_economic_health(median_income, unemployment_rate):
    """
    Income proxy: stronger income = premium units, better-quality tenants.
    Unemployment proxy: low unemployment = healthy tenant base, stable operators.
    Split 13 / 12 to give slightly more weight to unemployment (more current signal).
    """
    income = median_income or 0
    if income > 90_000: income_pts = 13
    elif income > 75_000: income_pts = 11
    elif income > 60_000: income_pts = 8
    elif income > 45_000: income_pts = 5
    else: income_pts = 2

    unemp = unemployment_rate if unemployment_rate is not None else 5.0
    if unemp < 3.0: unemp_pts = 12
    elif unemp < 4.0: unemp_pts = 10
    elif unemp < 5.0: unemp_pts = 7
    elif unemp < 6.5: unemp_pts = 4
    else: unemp_pts = 1

    return income_pts + unemp_pts


def _score_market_scale(population):
    """Larger population = more renters in absolute terms = higher ceiling for EliseAI ROI."""
    p = population or 0
    if p > 2_000_000: return 25
    if p > 1_000_000: return 21
    if p > 500_000:   return 17
    if p > 200_000:   return 12
    if p > 75_000:    return 7
    return 3


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

    total = market_size + rental_demand + econ_health + market_scale

    if total >= 80:   tier = "Hot"
    elif total >= 60: tier = "Warm"
    elif total >= 40: tier = "Cool"
    else:             tier = "Pass"

    return {
        "score": total,
        "tier": tier,
        "breakdown": {
            "marketSize":    {"score": market_size,   "max": 25, "label": "Market Size"},
            "rentalDemand":  {"score": rental_demand, "max": 25, "label": "Rental Demand"},
            "economicHealth":{"score": econ_health,   "max": 25, "label": "Economic Health"},
            "marketScale":   {"score": market_scale,  "max": 25, "label": "Market Scale"},
        },
    }
