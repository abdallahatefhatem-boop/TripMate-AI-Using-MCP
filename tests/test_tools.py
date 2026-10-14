from tools.flight_tool import (
    clean_text,
    country_name_to_code,
    parse_route,
    resolve_location_to_iata,
)


def test_clean_text():
    raw = "Flights to Paris under budget including hotel"
    cleaned = clean_text(raw)
    assert "paris" in cleaned
    assert "hotel" not in cleaned
    assert "flights" not in cleaned


def test_country_name_to_code():
    assert country_name_to_code("japan") == "JP"
    assert country_name_to_code("bangladesh") == "BD"
    assert country_name_to_code("united states") == "US"


def test_resolve_location_to_iata():
    assert resolve_location_to_iata("DAC") == "DAC"
    assert resolve_location_to_iata("Tokyo") in ["NRT", "HND"]
    assert resolve_location_to_iata("Dhaka") == "DAC"


def test_parse_route():
    dep, arr = parse_route("from Dhaka to Tokyo")
    assert dep == "DAC"
    assert arr in ["NRT", "HND"]

    dep_global, arr_global = parse_route("all country flight info")
    assert dep_global is None
    assert arr_global is None
