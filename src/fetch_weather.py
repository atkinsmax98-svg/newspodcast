"""Fetch a weather forecast from the free NOAA/National Weather Service API.

No API key required, but NWS requires a descriptive User-Agent header
identifying the application (per api.weather.gov policy).
"""

from __future__ import annotations

import requests

USER_AGENT = "daily-news-podcast (contact: github.com/atkinsmax98-svg/newspodcast)"


def get_forecast(latitude: float, longitude: float, location_name: str) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}

    points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    points_resp = requests.get(points_url, headers=headers, timeout=15)
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]

    forecast_resp = requests.get(forecast_url, headers=headers, timeout=15)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"]

    # Today and tonight (or the next two periods if run late in the day).
    today = periods[0] if periods else None
    tonight = periods[1] if len(periods) > 1 else None

    return {
        "location_name": location_name,
        "today": today,
        "tonight": tonight,
    }


def format_weather_for_prompt(forecast: dict) -> str:
    if not forecast.get("today"):
        return f"Weather data for {forecast['location_name']} was unavailable today."

    lines = [f"Weather for {forecast['location_name']}:"]
    today = forecast["today"]
    lines.append(
        f"- {today['name']}: {today['detailedForecast']}"
    )
    tonight = forecast.get("tonight")
    if tonight:
        lines.append(f"- {tonight['name']}: {tonight['detailedForecast']}")
    return "\n".join(lines)
