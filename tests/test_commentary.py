from cwf.commentary import EVENTS, commentary


def test_commentary_names_top_bucket():
    text = commentary("sony", 2026, {"revenue": {"yoy_pct": 0.003, "yoy_pct_usd": 0.015}},
                      {"rev_digital_software": 124.8e9, "rev_network_services": 93.3e9, "rev_hardware_other": -191.6e9},
                      {})
    assert "hardware & others" in text and "-¥191.6bn" in text
    assert "+0.3%" in text


def test_commentary_appends_event():
    text = commentary("microsoft", 2025, {"revenue": {"yoy_pct": 0.091, "yoy_pct_usd": 0.091}}, None, EVENTS)
    assert text.startswith("Gaming revenue +9.1% YoY") and "first full year" in text and "Activision" in text


def test_activision_partial_year_is_not_called_full():
    text = commentary("microsoft", 2024, {"revenue": {"yoy_pct": 0.39, "yoy_pct_usd": 0.39}}, None, EVENTS)
    assert "first full year" not in text and "Oct 2023" in text


def test_commentary_flags_fx_effect():
    text = commentary("sony", 2024, {"revenue": {"yoy_pct": 0.171, "yoy_pct_usd": 0.097}}, None, {})
    assert "weaker yen" in text and "+9.7% in USD" in text
    text = commentary("sony", 2024, {"revenue": {"yoy_pct": 0.10, "yoy_pct_usd": 0.12}}, None, {})
    assert "weaker yen" not in text and "stronger yen" not in text  # no FX note under 5 points


def test_commentary_without_prior_year():
    assert commentary("sony", 2013, {"revenue": {"yoy_pct": None, "yoy_pct_usd": None}}, None, {}) == \
        "First year in the series."
