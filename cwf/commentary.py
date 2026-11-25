"""One rule-based sentence per company-year, the kind a finance team writes beside a variance table."""

EVENTS = {
    ("microsoft", 2021): "Xbox Series X|S launched Nov 2020",
    ("microsoft", 2024): "includes Activision Blizzard from Oct 2023 (about 8.5 months)",
    ("microsoft", 2025): "first full year including Activision Blizzard",
    ("sony", 2021): "PS5 launched Nov 2020",
}
BUCKET_NAMES = {"rev_digital_software": "digital software & add-ons", "rev_network_services": "network services",
                "rev_hardware_other": "hardware & others"}
FX_NOTE_POINTS = 0.05


def _pct(x: float) -> str:
    return f"{x:+.1%}"


def _yen_bn(x: float) -> str:
    sign = "-" if x < 0 else "+"
    return f"{sign}¥{abs(x) / 1e9:,.1f}bn"


def commentary(company: str, fy: int, yoy: dict, mix: dict | None, events: dict) -> str:
    rev = yoy.get("revenue", {})
    local, usd = rev.get("yoy_pct"), rev.get("yoy_pct_usd")
    if local is None:
        parts = ["First year in the series"]
    elif company == "microsoft":
        parts = [f"Gaming revenue {_pct(local)} YoY"]
    else:
        head = f"G&NS revenue {_pct(local)} YoY in yen"
        if usd is not None and abs(local - usd) > FX_NOTE_POINTS:
            head += f" ({'weaker' if usd < local else 'stronger'} yen: {_pct(usd)} in USD)"
        parts = [head]
        if mix:
            bucket, change = max(mix.items(), key=lambda kv: abs(kv[1]))
            parts.append(f"biggest mover {BUCKET_NAMES[bucket]} ({_yen_bn(change)})")
        oi = yoy.get("operating_income", {}).get("yoy_pct")
        if oi is not None:
            parts.append(f"operating income {_pct(oi)}")
    if (company, fy) in events:
        parts.append(events[(company, fy)])
    return "; ".join(parts) + "."
