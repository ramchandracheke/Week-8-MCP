"""Open-Meteo geocoding, current weather, and forecast integration."""

from typing import Any

import httpx

from useful_mcp.http import TIMEOUT, get_json

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _locations(data: dict[str, Any]) -> list[dict[str, Any]]:
    results = data.get("results") or []
    if not isinstance(results, list):
        raise RuntimeError("The geocoding service returned an unexpected response.")
    locations = []
    for item in results[:5]:
        if not isinstance(item, dict):
            continue
        try:
            locations.append({
                "name": str(item["name"]),
                "country": item.get("country"),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "timezone": item.get("timezone"),
                "admin1": item.get("admin1"),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return locations


async def geocode(city: str) -> list[dict[str, Any]]:
    query = city.strip()
    if not query:
        raise ValueError("City must not be empty.")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data = await get_json(client, GEOCODING_URL, params={"name": query, "count": 5, "language": "en", "format": "json"})
    return _locations(data)


async def search_city(city: str) -> dict[str, Any]:
    """Find matching cities and return their country, coordinates, and timezone."""
    matches = await geocode(city)
    return {"query": city.strip(), "matches": matches, "ambiguous": len(matches) > 1}


async def _resolve(city: str) -> dict[str, Any]:
    matches = await geocode(city)
    if not matches:
        raise ValueError(f"No city matched {city!r}. Check the spelling or try a nearby larger city.")
    return matches[0]


async def get_current_weather(city: str) -> dict[str, Any]:
    """Fetch provider-reported current conditions for a city (not a forecast)."""
    location = await _resolve(city)
    params = {
        "latitude": location["latitude"], "longitude": location["longitude"], "timezone": location.get("timezone") or "auto",
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data = await get_json(client, FORECAST_URL, params=params)
    current = data.get("current")
    if not isinstance(current, dict):
        raise RuntimeError("The weather service did not include current conditions.")
    required = ("temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m", "weather_code", "time")
    if any(key not in current for key in required):
        raise RuntimeError("The weather service returned incomplete current conditions.")
    return {
        "location": location,
        "kind": "provider-reported current conditions",
        "temperature_c": current["temperature_2m"],
        "apparent_temperature_c": current["apparent_temperature"],
        "relative_humidity_percent": current["relative_humidity_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "weather_code": current["weather_code"],
        "timezone": data.get("timezone") or location.get("timezone"),
        "observed_at": current["time"],
    }


async def get_weather_forecast(city: str, days: int = 3) -> dict[str, Any]:
    """Return daily Open-Meteo forecast values in the city's local timezone."""
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 7:
        raise ValueError("days must be an integer from 1 to 7.")
    location = await _resolve(city)
    params = {
        "latitude": location["latitude"], "longitude": location["longitude"], "timezone": location.get("timezone") or "auto",
        "forecast_days": days,
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_probability_max,precipitation_sum,weather_code",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data = await get_json(client, FORECAST_URL, params=params)
    daily = data.get("daily")
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise RuntimeError("The weather service returned an incomplete forecast.")
    keys = ("temperature_2m_min", "temperature_2m_max", "precipitation_probability_max", "precipitation_sum", "weather_code")
    if any(not isinstance(daily.get(key), list) or len(daily[key]) != len(daily["time"]) for key in keys):
        raise RuntimeError("The weather service returned mismatched forecast data.")
    forecast = [
        {"date": date, "temperature_min_c": daily["temperature_2m_min"][i], "temperature_max_c": daily["temperature_2m_max"][i],
         "precipitation_probability_percent": daily["precipitation_probability_max"][i], "precipitation_mm": daily["precipitation_sum"][i],
         "weather_code": daily["weather_code"][i]}
        for i, date in enumerate(daily["time"])
    ]
    return {"location": location, "timezone": data.get("timezone") or location.get("timezone"), "days": forecast}
