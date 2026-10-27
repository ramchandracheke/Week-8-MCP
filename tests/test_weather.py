import httpx
import pytest

from useful_mcp import weather


@pytest.mark.asyncio
async def test_geocode_maps_provider_response(monkeypatch):
    async def fake_get_json(client, url, **kwargs):
        assert url == weather.GEOCODING_URL
        assert kwargs["params"]["name"] == "Paris"
        return {"results": [{"name": "Paris", "country": "France", "latitude": 48.85, "longitude": 2.35, "timezone": "Europe/Paris"}]}

    monkeypatch.setattr(weather, "get_json", fake_get_json)
    assert await weather.geocode(" Paris ") == [{"name": "Paris", "country": "France", "latitude": 48.85,
        "longitude": 2.35, "timezone": "Europe/Paris", "admin1": None}]


@pytest.mark.asyncio
async def test_unknown_city_returns_no_matches(monkeypatch):
    async def fake_get_json(*args, **kwargs):
        return {"results": None}

    monkeypatch.setattr(weather, "get_json", fake_get_json)
    assert await weather.search_city("No Such Place") == {"query": "No Such Place", "matches": [], "ambiguous": False}
    with pytest.raises(ValueError, match="No city matched"):
        await weather.get_current_weather("No Such Place")


@pytest.mark.asyncio
async def test_current_weather_parses_provider_fields(monkeypatch):
    async def fake_geocode(city):
        return [{"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.1, "timezone": "Europe/London"}]

    async def fake_get_json(client, url, **kwargs):
        assert url == weather.FORECAST_URL
        return {"timezone": "Europe/London", "current": {"temperature_2m": 17, "apparent_temperature": 16,
            "relative_humidity_2m": 65, "wind_speed_10m": 8, "weather_code": 3, "time": "2026-10-27T10:00"}}

    monkeypatch.setattr(weather, "geocode", fake_geocode)
    monkeypatch.setattr(weather, "get_json", fake_get_json)
    result = await weather.get_current_weather("London")
    assert result["kind"] == "provider-reported current conditions"
    assert result["temperature_c"] == 17
    assert result["observed_at"] == "2026-10-27T10:00"


@pytest.mark.asyncio
async def test_forecast_parses_daily_fields_and_local_dates(monkeypatch):
    async def fake_geocode(city):
        return [{"name": "Tokyo", "country": "Japan", "latitude": 35.6, "longitude": 139.7, "timezone": "Asia/Tokyo"}]

    async def fake_get_json(client, url, **kwargs):
        assert kwargs["params"]["forecast_days"] == 2
        return {"timezone": "Asia/Tokyo", "daily": {"time": ["2026-10-27", "2026-10-28"],
            "temperature_2m_min": [12, 13], "temperature_2m_max": [20, 21],
            "precipitation_probability_max": [10, 40], "precipitation_sum": [0, 2.5], "weather_code": [1, 61]}}

    monkeypatch.setattr(weather, "geocode", fake_geocode)
    monkeypatch.setattr(weather, "get_json", fake_get_json)
    result = await weather.get_weather_forecast("Tokyo", 2)
    assert result["timezone"] == "Asia/Tokyo"
    assert result["days"][1]["date"] == "2026-10-28"
    assert result["days"][1]["precipitation_mm"] == 2.5


@pytest.mark.asyncio
async def test_forecast_days_validation():
    for invalid in (0, 8, True, 2.5):
        with pytest.raises(ValueError, match="days must be an integer"):
            await weather.get_weather_forecast("Paris", invalid)
