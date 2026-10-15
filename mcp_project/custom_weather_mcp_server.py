import os

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

mcp = FastMCP("weather")


@mcp.tool()
def get_current_weather(city: str) -> str:
    """Get the current weather for a specific city."""
    if not OPENWEATHER_API_KEY:
        return "Weather information unavailable: OPENWEATHER_API_KEY is not configured."

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            main = data.get("main", {})
            weather_desc = data.get("weather", [{}])[0].get("description", "N/A")
            temp = main.get("temp", "N/A")
            humidity = main.get("humidity", "N/A")
            return f"Current weather in {city}: {weather_desc}, Temperature: {temp}°C, Humidity: {humidity}%"
        else:
            return f"Unable to fetch current weather for {city} (HTTP {response.status_code})."
    except Exception as e:
        return f"Error fetching current weather for {city}: {str(e)}"


@mcp.tool()
def get_forecast(city: str) -> str:
    """Get the weather forecast for a specific city."""
    if not OPENWEATHER_API_KEY:
        return "Forecast information unavailable: OPENWEATHER_API_KEY is not configured."

    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            forecast_list = data.get("list", [])[:5]
            summaries = []
            for item in forecast_list:
                dt_txt = item.get("dt_txt", "")
                temp = item.get("main", {}).get("temp", "N/A")
                desc = item.get("weather", [{}])[0].get("description", "")
                summaries.append(f"{dt_txt}: {temp}°C, {desc}")
            return f"Forecast for {city}:\n" + "\n".join(summaries)
        else:
            return f"Unable to fetch forecast for {city} (HTTP {response.status_code})."
    except Exception as e:
        return f"Error fetching forecast for {city}: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
