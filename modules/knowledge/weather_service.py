"""
Weather Service
Provides weather forecast data for agricultural planning.
Uses a simulated dataset with realistic Indian weather patterns.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Simulated weather data for major agricultural regions ─────────────────────
REGIONAL_WEATHER = {
    "tamil nadu": {
        "base_temp": 32, "humidity": 70, "rainfall_mm": 80,
        "season": "Northeast Monsoon", "soil_moisture": "moderate",
    },
    "punjab": {
        "base_temp": 28, "humidity": 55, "rainfall_mm": 45,
        "season": "Kharif", "soil_moisture": "good",
    },
    "maharashtra": {
        "base_temp": 30, "humidity": 65, "rainfall_mm": 60,
        "season": "Southwest Monsoon", "soil_moisture": "moderate",
    },
    "uttar pradesh": {
        "base_temp": 29, "humidity": 60, "rainfall_mm": 50,
        "season": "Rabi", "soil_moisture": "good",
    },
    "karnataka": {
        "base_temp": 27, "humidity": 68, "rainfall_mm": 70,
        "season": "Southwest Monsoon", "soil_moisture": "moderate",
    },
    "andhra pradesh": {
        "base_temp": 33, "humidity": 72, "rainfall_mm": 65,
        "season": "Northeast Monsoon", "soil_moisture": "low",
    },
    "madhya pradesh": {
        "base_temp": 30, "humidity": 50, "rainfall_mm": 55,
        "season": "Kharif", "soil_moisture": "moderate",
    },
    "rajasthan": {
        "base_temp": 35, "humidity": 30, "rainfall_mm": 20,
        "season": "Arid", "soil_moisture": "low",
    },
    "west bengal": {
        "base_temp": 29, "humidity": 80, "rainfall_mm": 100,
        "season": "Monsoon", "soil_moisture": "high",
    },
    "kerala": {
        "base_temp": 28, "humidity": 85, "rainfall_mm": 120,
        "season": "Southwest Monsoon", "soil_moisture": "high",
    },
}

DEFAULT_WEATHER = {
    "base_temp": 30, "humidity": 60, "rainfall_mm": 50,
    "season": "General", "soil_moisture": "moderate",
}


class WeatherService:
    """Provides weather forecasts and agricultural weather advisories."""

    def get_weather(self, location: Optional[str] = None, date: Optional[str] = None) -> dict:
        """
        Get weather forecast for a location.

        Args:
            location: District/state name.
            date: Date string (optional).

        Returns:
            Structured weather data dict.
        """
        logger.info(f"Weather query: location={location}, date={date}")

        # Find matching regional data
        region_data = DEFAULT_WEATHER
        matched_region = "India (General)"

        if location:
            location_lower = location.lower().strip()
            for region, data in REGIONAL_WEATHER.items():
                if region in location_lower or location_lower in region:
                    region_data = data
                    matched_region = region.title()
                    break

        # Generate forecast with realistic variation
        forecast = self._generate_forecast(region_data, matched_region, date)

        # Add agricultural advisory
        forecast["advisory"] = self._get_agricultural_advisory(forecast)

        logger.info(f"Weather result: {forecast['location']} — {forecast['condition']}")
        return forecast

    def _generate_forecast(self, base: dict, region: str, date: Optional[str]) -> dict:
        """Generate a realistic weather forecast."""
        # Add natural variation
        temp_variation = random.uniform(-3, 3)
        humidity_variation = random.uniform(-10, 10)

        temp = round(base["base_temp"] + temp_variation, 1)
        temp_min = round(temp - random.uniform(4, 8), 1)
        temp_max = round(temp + random.uniform(2, 5), 1)
        humidity = min(100, max(10, round(base["humidity"] + humidity_variation)))
        rainfall = round(base["rainfall_mm"] * random.uniform(0.5, 1.5), 1)

        # Determine condition
        if rainfall > 80:
            condition = "Heavy Rain Expected"
            icon = "🌧️"
        elif rainfall > 40:
            condition = "Moderate Rain"
            icon = "🌦️"
        elif rainfall > 10:
            condition = "Light Showers"
            icon = "⛅"
        elif humidity > 75:
            condition = "Cloudy & Humid"
            icon = "☁️"
        else:
            condition = "Sunny & Clear"
            icon = "☀️"

        # Wind
        wind_speed = round(random.uniform(5, 25), 1)
        wind_dir = random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

        forecast_date = date or datetime.now().strftime("%Y-%m-%d")

        return {
            "location": region,
            "date": forecast_date,
            "condition": condition,
            "icon": icon,
            "temperature": {
                "current": temp,
                "min": temp_min,
                "max": temp_max,
                "unit": "°C",
            },
            "humidity_percent": humidity,
            "rainfall_mm": rainfall,
            "wind": {
                "speed_kmh": wind_speed,
                "direction": wind_dir,
            },
            "soil_moisture": base["soil_moisture"],
            "season": base["season"],
            "5_day_outlook": self._get_5day_outlook(base),
        }

    def _get_5day_outlook(self, base: dict) -> list:
        """Generate a 5-day weather outlook."""
        outlook = []
        for i in range(1, 6):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            rain = round(base["rainfall_mm"] * random.uniform(0.3, 1.8), 1)
            temp = round(base["base_temp"] + random.uniform(-4, 4), 1)

            if rain > 60:
                cond = "Rainy"
            elif rain > 20:
                cond = "Partly Cloudy"
            else:
                cond = "Sunny"

            outlook.append({
                "date": date,
                "condition": cond,
                "temp_c": temp,
                "rainfall_mm": rain,
            })
        return outlook

    def _get_agricultural_advisory(self, forecast: dict) -> str:
        """Generate farming advisory based on weather conditions."""
        advisories = []

        rainfall = forecast["rainfall_mm"]
        temp = forecast["temperature"]["current"]
        humidity = forecast["humidity_percent"]

        if rainfall > 80:
            advisories.append("Heavy rainfall expected. Ensure proper drainage in fields.")
            advisories.append("Delay fertilizer application to prevent nutrient washout.")
            advisories.append("Monitor crops for waterlogging damage.")
        elif rainfall > 40:
            advisories.append("Moderate rain expected. Good conditions for sowing.")
            advisories.append("Apply fertilizers after rain for better absorption.")
        elif rainfall < 10:
            advisories.append("Dry conditions expected. Ensure irrigation is available.")
            advisories.append("Consider mulching to retain soil moisture.")

        if temp > 38:
            advisories.append("High temperature alert. Provide shade for sensitive crops.")
            advisories.append("Irrigate during early morning or evening to minimize evaporation.")
        elif temp < 10:
            advisories.append("Cold conditions. Protect crops from frost damage.")

        if humidity > 85:
            advisories.append("High humidity may increase risk of fungal diseases. Apply preventive fungicide.")

        return " | ".join(advisories) if advisories else "Normal weather conditions. Continue regular farming activities."
