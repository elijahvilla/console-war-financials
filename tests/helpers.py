"""Shared test builders (test-only code)."""
from datetime import date, timedelta

from cwf.extract import Row

GAAP = "us-gaap"
IFRS = "ifrs"


def ms(fy, value, filed=None, acc=None):
    filed = filed or date(fy, 7, 30)
    return Row("microsoft", fy, date(fy - 1, 7, 1), date(fy, 6, 30), "revenue", value, "USD",
               acc or f"ms-{filed.year}", filed, "RevenueFromContractWithCustomerExcludingAssessedTax", GAAP)


def sony(fy, metric, value, filed=None, acc=None, basis=IFRS, concept=None):
    filed = filed or date(fy, 6, 20)
    concept = concept or ("Revenue" if basis == IFRS else "Revenues")
    return Row("sony", fy, date(fy - 1, 4, 1), date(fy, 3, 31), metric, value, "JPY",
               acc or f"sony-{filed.year}", filed, concept, basis)


def flat_fx(rate=150.0, start=date(2010, 1, 1), end=date(2027, 12, 31)):
    out, d = {}, start
    while d <= end:
        if d.weekday() < 5:
            out[d] = rate
        d += timedelta(days=1)
    return out


def clean_sony_year(fy, scale=1.0, filed=None):
    """A consistent Sony year: buckets sum to external."""
    vals = {"revenue": 1000 * scale, "revenue_external": 900 * scale, "operating_income": 100 * scale,
            "rev_digital_software": 500 * scale, "rev_network_services": 150 * scale, "rev_hardware_other": 250 * scale}
    return [sony(fy, m, v, filed=filed) for m, v in vals.items()]
