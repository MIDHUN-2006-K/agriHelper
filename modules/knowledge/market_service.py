"""
Market Price Service
Provides agricultural commodity market prices (simulated for demo).
Based on realistic Indian mandi price patterns.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Simulated market price data (INR per quintal) ────────────────────────────
COMMODITY_PRICES = {
    "rice": {
        "msp": 2183,  # MSP 2024-25
        "market_range": (1900, 2500),
        "unit": "quintal",
        "grade": "Common",
        "markets": {
            "Tamil Nadu": {"avg": 2250, "high": 2450, "low": 2050},
            "Punjab": {"avg": 2200, "high": 2380, "low": 2100},
            "West Bengal": {"avg": 2100, "high": 2300, "low": 1950},
            "Andhra Pradesh": {"avg": 2180, "high": 2400, "low": 2000},
        },
    },
    "wheat": {
        "msp": 2275,
        "market_range": (2000, 2600),
        "unit": "quintal",
        "grade": "FAQ",
        "markets": {
            "Punjab": {"avg": 2300, "high": 2500, "low": 2150},
            "Uttar Pradesh": {"avg": 2250, "high": 2450, "low": 2100},
            "Madhya Pradesh": {"avg": 2280, "high": 2480, "low": 2100},
            "Rajasthan": {"avg": 2200, "high": 2400, "low": 2050},
        },
    },
    "sugarcane": {
        "msp": 315,  # FRP per quintal
        "market_range": (300, 400),
        "unit": "quintal",
        "grade": "Standard",
        "markets": {
            "Uttar Pradesh": {"avg": 350, "high": 380, "low": 315},
            "Maharashtra": {"avg": 330, "high": 370, "low": 300},
            "Karnataka": {"avg": 340, "high": 375, "low": 310},
        },
    },
    "tomato": {
        "msp": None,
        "market_range": (500, 4000),
        "unit": "quintal",
        "grade": "Fresh",
        "markets": {
            "Tamil Nadu": {"avg": 1500, "high": 3500, "low": 600},
            "Karnataka": {"avg": 1800, "high": 3800, "low": 700},
            "Maharashtra": {"avg": 1600, "high": 3200, "low": 500},
            "Andhra Pradesh": {"avg": 1400, "high": 3000, "low": 550},
        },
    },
    "cotton": {
        "msp": 7121,
        "market_range": (6000, 8500),
        "unit": "quintal",
        "grade": "Medium Staple",
        "markets": {
            "Maharashtra": {"avg": 7200, "high": 8000, "low": 6500},
            "Gujarat": {"avg": 7300, "high": 8200, "low": 6600},
            "Telangana": {"avg": 7100, "high": 7900, "low": 6400},
        },
    },
    "maize": {
        "msp": 2090,
        "market_range": (1800, 2500),
        "unit": "quintal",
        "grade": "Common",
        "markets": {
            "Karnataka": {"avg": 2100, "high": 2400, "low": 1850},
            "Madhya Pradesh": {"avg": 2050, "high": 2350, "low": 1800},
            "Rajasthan": {"avg": 2000, "high": 2300, "low": 1750},
        },
    },
    "onion": {
        "msp": None,
        "market_range": (500, 5000),
        "unit": "quintal",
        "grade": "Medium",
        "markets": {
            "Maharashtra": {"avg": 2000, "high": 4500, "low": 600},
            "Karnataka": {"avg": 1800, "high": 4000, "low": 500},
            "Madhya Pradesh": {"avg": 1700, "high": 3800, "low": 550},
        },
    },
    "potato": {
        "msp": None,
        "market_range": (400, 2500),
        "unit": "quintal",
        "grade": "Medium",
        "markets": {
            "Uttar Pradesh": {"avg": 1200, "high": 2200, "low": 500},
            "West Bengal": {"avg": 1100, "high": 2000, "low": 450},
            "Punjab": {"avg": 1300, "high": 2300, "low": 550},
        },
    },
}


class MarketService:
    """Provides agricultural commodity market price information."""

    def get_prices(
        self,
        crop_name: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        """
        Get market prices for a commodity.

        Args:
            crop_name: Name of the crop/commodity.
            location: State or market location.

        Returns:
            Structured market price data.
        """
        logger.info(f"Market price query: crop={crop_name}, location={location}")

        crop = (crop_name or "").lower().strip()

        if crop not in COMMODITY_PRICES:
            return self._commodity_not_found(crop)

        commodity = COMMODITY_PRICES[crop]

        # Find location-specific prices
        location_prices = None
        matched_market = None
        if location:
            loc_lower = location.lower()
            for market, prices in commodity["markets"].items():
                if market.lower() in loc_lower or loc_lower in market.lower():
                    location_prices = prices
                    matched_market = market
                    break

        # If no location match, aggregate all markets
        if location_prices is None:
            all_prices = list(commodity["markets"].values())
            location_prices = {
                "avg": round(sum(p["avg"] for p in all_prices) / len(all_prices)),
                "high": max(p["high"] for p in all_prices),
                "low": min(p["low"] for p in all_prices),
            }
            matched_market = "All India Average"

        # Add realistic daily variation
        variation = random.uniform(-0.05, 0.05)
        today_price = round(location_prices["avg"] * (1 + variation))

        result = {
            "crop": crop,
            "market": matched_market,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "prices": {
                "today": today_price,
                "average": location_prices["avg"],
                "highest": location_prices["high"],
                "lowest": location_prices["low"],
                "unit": f"INR per {commodity['unit']}",
            },
            "msp": commodity["msp"],
            "msp_note": f"MSP (Minimum Support Price): ₹{commodity['msp']}/{commodity['unit']}" if commodity["msp"] else "No MSP declared for this commodity",
            "grade": commodity["grade"],
            "trend": self._get_price_trend(crop),
            "all_markets": {k: v for k, v in commodity["markets"].items()},
            "advice": self._get_market_advice(today_price, commodity),
        }

        logger.info(f"Market price: {crop} @ ₹{today_price}/{commodity['unit']} ({matched_market})")
        return result

    def _get_price_trend(self, crop: str) -> dict:
        """Simulate price trend for the last 7 days."""
        base = COMMODITY_PRICES[crop]["market_range"]
        avg = (base[0] + base[1]) / 2
        trend = []
        for i in range(7, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            price = round(avg * random.uniform(0.9, 1.1))
            trend.append({"date": date, "price": price})

        direction = "rising" if trend[-1]["price"] > trend[0]["price"] else "falling"
        return {"direction": direction, "last_7_days": trend}

    def _get_market_advice(self, current_price: int, commodity: dict) -> str:
        """Generate market advisory based on current price."""
        msp = commodity.get("msp")
        high = commodity["market_range"][1]
        low = commodity["market_range"][0]
        mid = (high + low) / 2

        if msp and current_price < msp:
            return f"Current price is below MSP (₹{msp}). Consider selling at government procurement centers."
        elif current_price > mid * 1.1:
            return "Prices are above average. Consider selling now for good returns."
        elif current_price < mid * 0.9:
            return "Prices are below average. Consider storing if possible and wait for better prices."
        else:
            return "Prices are around average levels. Monitor daily trends before making selling decisions."

    def _commodity_not_found(self, crop: str) -> dict:
        """Handle unknown commodity."""
        available = list(COMMODITY_PRICES.keys())
        return {
            "crop": crop,
            "error": f"No price data available for '{crop}'.",
            "available_commodities": available,
            "suggestion": f"Try one of: {', '.join(available)}",
        }

    def list_commodities(self) -> list:
        """Return list of commodities with available price data."""
        return list(COMMODITY_PRICES.keys())
