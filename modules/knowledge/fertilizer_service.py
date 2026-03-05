"""
Fertilizer Recommendation Service
Provides fertilizer recommendations based on crop, soil type, and region.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Comprehensive fertilizer database ─────────────────────────────────────────
FERTILIZER_DB = {
    "rice": {
        "red soil": {
            "fertilizer": "NPK 20-10-10",
            "nitrogen_kg_ha": 120,
            "phosphorus_kg_ha": 60,
            "potassium_kg_ha": 40,
            "application": "Apply in 3 split doses: 50% N at transplanting, 25% at tillering, 25% at panicle initiation.",
            "organic_alternative": "Vermicompost @ 5 tonnes/hectare + Azospirillum @ 2 kg/hectare",
        },
        "black soil": {
            "fertilizer": "NPK 18-18-18",
            "nitrogen_kg_ha": 100,
            "phosphorus_kg_ha": 50,
            "potassium_kg_ha": 50,
            "application": "Apply basal dose of full P and K with 50% N. Top dress remaining N in 2 splits.",
            "organic_alternative": "FYM @ 10 tonnes/hectare + Biofertilizers",
        },
        "alluvial soil": {
            "fertilizer": "Urea + DAP + MOP",
            "nitrogen_kg_ha": 110,
            "phosphorus_kg_ha": 55,
            "potassium_kg_ha": 45,
            "application": "Basal: Full P, K, 1/3 N. First top dress at tillering, second at panicle.",
            "organic_alternative": "Green manure + Azolla @ 500 kg/hectare",
        },
    },
    "wheat": {
        "red soil": {
            "fertilizer": "Potash + Urea",
            "nitrogen_kg_ha": 140,
            "phosphorus_kg_ha": 60,
            "potassium_kg_ha": 279,
            "application": "Apply in split doses for better nutrient absorption. Basal: Full P, K, 50% N.",
            "organic_alternative": "Vermicompost @ 4 tonnes/hectare + PSB",
        },
        "black soil": {
            "fertilizer": "DAP + Urea",
            "nitrogen_kg_ha": 120,
            "phosphorus_kg_ha": 60,
            "potassium_kg_ha": 40,
            "application": "Basal dose with full P and K. Top-dress N in 2 splits at CRI and boot stage.",
            "organic_alternative": "FYM @ 8 tonnes/hectare + Azotobacter",
        },
        "alluvial soil": {
            "fertilizer": "NPK 12-32-16",
            "nitrogen_kg_ha": 130,
            "phosphorus_kg_ha": 65,
            "potassium_kg_ha": 45,
            "application": "Apply 50% N + full P + full K as basal. Remaining N in 2 equal splits.",
            "organic_alternative": "Neem cake @ 2 tonnes/hectare + Biofertilizers",
        },
    },
    "sugarcane": {
        "red soil": {
            "fertilizer": "NPK 150-60-60",
            "nitrogen_kg_ha": 250,
            "phosphorus_kg_ha": 100,
            "potassium_kg_ha": 120,
            "application": "Apply N in 4 splits: at planting, 45 days, 90 days, and 120 days.",
            "organic_alternative": "Press mud @ 10 tonnes/hectare + Acetobacter",
        },
        "black soil": {
            "fertilizer": "Urea + SSP + MOP",
            "nitrogen_kg_ha": 200,
            "phosphorus_kg_ha": 80,
            "potassium_kg_ha": 80,
            "application": "Basal P and K. N in 3-4 splits at monthly intervals.",
            "organic_alternative": "FYM @ 15 tonnes/hectare + Biofertilizers",
        },
    },
    "tomato": {
        "red soil": {
            "fertilizer": "NPK 19-19-19 + Calcium Nitrate",
            "nitrogen_kg_ha": 150,
            "phosphorus_kg_ha": 80,
            "potassium_kg_ha": 100,
            "application": "Basal: Full P, 50% K, 30% N. Remaining through fertigation at weekly intervals.",
            "organic_alternative": "Vermicompost @ 5 tonnes + Bone meal @ 500 kg/hectare",
        },
        "black soil": {
            "fertilizer": "DAP + MOP + Micronutrient mix",
            "nitrogen_kg_ha": 120,
            "phosphorus_kg_ha": 70,
            "potassium_kg_ha": 80,
            "application": "Apply in 4-5 splits through drip. Include micro-nutrients at flowering.",
            "organic_alternative": "Neem cake + Panchagavya spray",
        },
    },
    "cotton": {
        "black soil": {
            "fertilizer": "Urea + SSP + MOP",
            "nitrogen_kg_ha": 120,
            "phosphorus_kg_ha": 60,
            "potassium_kg_ha": 60,
            "application": "Basal: 25% N + full P + 50% K. Top dress N at square and boll formation.",
            "organic_alternative": "FYM @ 12 tonnes/hectare + Azospirillum",
        },
        "red soil": {
            "fertilizer": "NPK 20-20-20 + Sulphur",
            "nitrogen_kg_ha": 100,
            "phosphorus_kg_ha": 50,
            "potassium_kg_ha": 50,
            "application": "Split application with emphasis on K during boll development.",
            "organic_alternative": "Vermicompost + Trichoderma",
        },
    },
    "maize": {
        "red soil": {
            "fertilizer": "NPK 20-10-10 + Zinc Sulphate",
            "nitrogen_kg_ha": 150,
            "phosphorus_kg_ha": 75,
            "potassium_kg_ha": 40,
            "application": "Basal: Full P, K, 33% N, ZnSO4 @ 25kg/ha. Top dress N at knee-high and tasseling.",
            "organic_alternative": "FYM @ 10 tonnes + Azotobacter + PSB",
        },
        "alluvial soil": {
            "fertilizer": "Urea + DAP",
            "nitrogen_kg_ha": 120,
            "phosphorus_kg_ha": 60,
            "potassium_kg_ha": 40,
            "application": "Apply in 3 splits: basal, knee-high, pre-tassel.",
            "organic_alternative": "Green manure + Biofertilizers",
        },
    },
}

# Default recommendation when crop/soil combo is not found
DEFAULT_RECOMMENDATION = {
    "fertilizer": "NPK 15-15-15 (Balanced)",
    "nitrogen_kg_ha": 100,
    "phosphorus_kg_ha": 50,
    "potassium_kg_ha": 50,
    "application": "Apply balanced fertilizer in 2-3 split doses. Get soil tested for specific recommendations.",
    "organic_alternative": "Well-decomposed FYM @ 8-10 tonnes/hectare",
}


class FertilizerService:
    """Provides crop and soil-specific fertilizer recommendations."""

    def get_recommendation(
        self,
        crop_name: Optional[str] = None,
        soil_type: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        """
        Get fertilizer recommendation.

        Args:
            crop_name: Name of the crop.
            soil_type: Type of soil.
            location: Location (used for regional defaults).

        Returns:
            Structured fertilizer recommendation dict.
        """
        logger.info(f"Fertilizer query: crop={crop_name}, soil={soil_type}, location={location}")

        crop = (crop_name or "").lower().strip()
        soil = (soil_type or "").lower().strip()

        # Look up in database
        if crop in FERTILIZER_DB:
            crop_data = FERTILIZER_DB[crop]
            if soil in crop_data:
                rec = crop_data[soil]
            else:
                # Use first available soil type for this crop
                first_soil = list(crop_data.keys())[0]
                rec = crop_data[first_soil]
                soil = soil or first_soil
        else:
            rec = DEFAULT_RECOMMENDATION

        result = {
            "crop": crop or "general",
            "soil_type": soil or "not specified",
            "location": location or "not specified",
            "recommendation": {
                "primary_fertilizer": rec["fertilizer"],
                "nitrogen_kg_per_hectare": rec["nitrogen_kg_ha"],
                "phosphorus_kg_per_hectare": rec["phosphorus_kg_ha"],
                "potassium_kg_per_hectare": rec["potassium_kg_ha"],
                "application_method": rec["application"],
                "organic_alternative": rec["organic_alternative"],
            },
            "general_tips": self._get_general_tips(crop, soil),
            "source": "AgriHelper Fertilizer Knowledge Base",
        }

        logger.info(f"Fertilizer recommendation: {rec['fertilizer']} for {crop} on {soil}")
        return result

    def _get_general_tips(self, crop: str, soil: str) -> list:
        """General fertilizer application tips."""
        tips = [
            "Always get soil tested before applying fertilizers for accurate recommendations.",
            "Apply fertilizers when soil has adequate moisture for better absorption.",
            "Avoid fertilizer application during heavy rains to prevent nutrient runoff.",
        ]

        if soil == "red soil":
            tips.append("Red soil is generally acidic. Consider lime application if pH < 5.5.")
        elif soil == "black soil":
            tips.append("Black soil retains moisture well. Avoid over-irrigation after fertilizer application.")

        if crop in ["rice", "sugarcane"]:
            tips.append(f"{crop.title()} is a heavy feeder. Monitor crop growth and adjust doses.")

        return tips

    def list_available_crops(self) -> list:
        """Return list of crops with available recommendations."""
        return list(FERTILIZER_DB.keys())
