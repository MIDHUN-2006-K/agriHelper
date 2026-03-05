"""
Government Scheme Service
Provides information on agricultural government schemes and subsidies
available to Indian farmers.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Government schemes database ──────────────────────────────────────────────
SCHEMES_DB = [
    {
        "id": "pm_kisan",
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "name_ta": "பிரதம மந்திரி கிசான் சம்மான் நிதி",
        "name_hi": "प्रधान मंत्री किसान सम्मान निधि",
        "description": "Direct income support of ₹6,000 per year to all landholding farmer families, paid in 3 equal installments of ₹2,000 each.",
        "eligibility": [
            "All landholding farmer families",
            "Must have cultivable land",
            "Aadhaar-linked bank account required",
        ],
        "benefit": "₹6,000 per year (₹2,000 x 3 installments)",
        "how_to_apply": "Visit https://pmkisan.gov.in or contact local agriculture office",
        "documents_required": ["Aadhaar Card", "Land records", "Bank account details"],
        "category": "income_support",
        "states": "all",
    },
    {
        "id": "pmfby",
        "name": "PMFBY (Pradhan Mantri Fasal Bima Yojana)",
        "name_ta": "பிரதம மந்திரி பயிர் காப்பீடு திட்டம்",
        "name_hi": "प्रधान मंत्री फसल बीमा योजना",
        "description": "Crop insurance scheme that provides financial support to farmers suffering crop loss due to natural calamities, pests, and diseases.",
        "eligibility": [
            "All farmers growing notified crops",
            "Both loanee and non-loanee farmers",
            "Available for Kharif and Rabi seasons",
        ],
        "benefit": "Premium: 2% for Kharif, 1.5% for Rabi crops. Full claim on crop loss.",
        "how_to_apply": "Through banks, CSC centers, or https://pmfby.gov.in",
        "documents_required": ["Land records", "Sowing certificate", "Bank account", "Aadhaar"],
        "category": "crop_insurance",
        "states": "all",
    },
    {
        "id": "kcc",
        "name": "Kisan Credit Card (KCC)",
        "name_ta": "கிசான் கிரெடிட் கார்டு",
        "name_hi": "किसान क्रेडिट कार्ड",
        "description": "Credit facility for farmers to meet their agricultural and allied activities needs at subsidized interest rates.",
        "eligibility": [
            "Individual farmers (owner cultivators)",
            "Tenant farmers and sharecroppers",
            "Self-Help Groups or Joint Liability Groups",
        ],
        "benefit": "Credit limit up to ₹3 lakh at 4% interest rate (with subvention). Crop loan + working capital.",
        "how_to_apply": "Apply at any commercial bank, RRB, or cooperative bank",
        "documents_required": ["Land records", "Identity proof", "Passport photo", "Bank details"],
        "category": "credit",
        "states": "all",
    },
    {
        "id": "soil_health_card",
        "name": "Soil Health Card Scheme",
        "name_ta": "மண் ஆரோக்கிய அட்டை திட்டம்",
        "name_hi": "मृदा स्वास्थ्य कार्ड योजना",
        "description": "Government scheme that provides soil health cards to farmers with crop-wise recommendations for nutrients and fertilizers.",
        "eligibility": [
            "All farmers across India",
            "Free soil testing every 2 years",
        ],
        "benefit": "Free soil testing + personalized fertilizer and nutrient recommendations",
        "how_to_apply": "Contact local agriculture department or Krishi Vigyan Kendra",
        "documents_required": ["Land details", "Identity proof"],
        "category": "soil_health",
        "states": "all",
    },
    {
        "id": "pmksy",
        "name": "PMKSY (Pradhan Mantri Krishi Sinchai Yojana)",
        "name_ta": "பிரதம மந்திரி விவசாய நீர்ப்பாசன திட்டம்",
        "name_hi": "प्रधान मंत्री कृषि सिंचाई योजना",
        "description": "Scheme to improve farm productivity by ensuring irrigation to every farm ('Har Khet Ko Paani'). Supports micro-irrigation, drip, and sprinkler systems.",
        "eligibility": [
            "All farmer categories",
            "Special focus on small and marginal farmers",
            "55% subsidy for small farmers, 45% for others",
        ],
        "benefit": "Up to 55% subsidy on drip and sprinkler irrigation systems",
        "how_to_apply": "Apply through state agriculture department or https://pmksy.gov.in",
        "documents_required": ["Land records", "Quotation from approved supplier", "Bank details"],
        "category": "irrigation",
        "states": "all",
    },
    {
        "id": "e_nam",
        "name": "eNAM (National Agriculture Market)",
        "name_ta": "தேசிய விவசாய சந்தை (eNAM)",
        "name_hi": "राष्ट्रीय कृषि बाजार (eNAM)",
        "description": "Online trading platform for agricultural commodities. Helps farmers get better prices by connecting them to buyers nationwide.",
        "eligibility": [
            "All farmers with produce to sell",
            "APMC registration required in some states",
        ],
        "benefit": "Access to nationwide buyers, transparent pricing, direct payment to bank",
        "how_to_apply": "Register at https://enam.gov.in or visit nearest eNAM mandi",
        "documents_required": ["Aadhaar", "Bank account", "Produce details"],
        "category": "marketing",
        "states": "all",
    },
    {
        "id": "pkvy",
        "name": "Paramparagat Krishi Vikas Yojana (PKVY)",
        "name_ta": "பரம்பரையான விவசாய வளர்ச்சி திட்டம்",
        "name_hi": "परम्परागत कृषि विकास योजना",
        "description": "Promotes organic farming through cluster approach. Financial assistance for organic inputs, certification, and marketing.",
        "eligibility": [
            "Farmers willing to adopt organic farming",
            "Cluster of 50 or more farmers",
            "Minimum 20 hectares cluster area",
        ],
        "benefit": "₹50,000 per hectare over 3 years for organic farming adoption",
        "how_to_apply": "Contact district agriculture officer or state organic farming mission",
        "documents_required": ["Land records", "Farmer group formation", "Bank details"],
        "category": "organic_farming",
        "states": "all",
    },
    {
        "id": "agri_infra_fund",
        "name": "Agriculture Infrastructure Fund (AIF)",
        "name_ta": "விவசாய உள்கட்டமைப்பு நிதி",
        "name_hi": "कृषि अवसंरचना कोष",
        "description": "₹1 lakh crore financing facility for post-harvest management infrastructure and community farming assets.",
        "eligibility": [
            "Farmers, FPOs, PACS, marketing cooperative societies",
            "Agri-entrepreneurs, start-ups",
        ],
        "benefit": "Interest subvention of 3% on loans up to ₹2 crore. Credit guarantee support.",
        "how_to_apply": "Apply through https://agriinfra.dac.gov.in or partner banks",
        "documents_required": ["Project report", "Land documents", "KYC", "Bank details"],
        "category": "infrastructure",
        "states": "all",
    },
]


class SchemeService:
    """Provides information about government agricultural schemes."""

    def search_schemes(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        """
        Search for relevant government schemes.

        Args:
            query: Free text search query.
            category: Specific category filter.
            location: State/region filter.

        Returns:
            List of matching schemes.
        """
        logger.info(f"Scheme query: query={query}, category={category}, location={location}")

        results = SCHEMES_DB.copy()

        # Filter by category
        if category:
            cat_lower = category.lower()
            category_map = {
                "insurance": "crop_insurance",
                "crop insurance": "crop_insurance",
                "credit": "credit",
                "loan": "credit",
                "subsidy": "income_support",
                "income": "income_support",
                "irrigation": "irrigation",
                "water": "irrigation",
                "market": "marketing",
                "price": "marketing",
                "organic": "organic_farming",
                "soil": "soil_health",
            }
            mapped = category_map.get(cat_lower, cat_lower)
            results = [s for s in results if s["category"] == mapped]

        # Filter by text query
        if query:
            query_lower = query.lower()
            keywords = query_lower.split()
            scored = []
            for scheme in results:
                score = 0
                searchable = f"{scheme['name']} {scheme['description']} {scheme['category']}".lower()
                for kw in keywords:
                    if kw in searchable:
                        score += 1
                if score > 0:
                    scored.append((score, scheme))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [s for _, s in scored]

        # Format output
        return {
            "query": query or "all",
            "total_results": len(results),
            "schemes": [
                {
                    "name": s["name"],
                    "name_ta": s.get("name_ta", ""),
                    "name_hi": s.get("name_hi", ""),
                    "description": s["description"],
                    "eligibility": s["eligibility"],
                    "benefit": s["benefit"],
                    "how_to_apply": s["how_to_apply"],
                    "documents_required": s["documents_required"],
                    "category": s["category"],
                }
                for s in results
            ],
        }

    def get_scheme_by_id(self, scheme_id: str) -> Optional[dict]:
        """Get a specific scheme by ID."""
        for scheme in SCHEMES_DB:
            if scheme["id"] == scheme_id:
                return scheme
        return None

    def list_categories(self) -> list:
        """List available scheme categories."""
        return list(set(s["category"] for s in SCHEMES_DB))
