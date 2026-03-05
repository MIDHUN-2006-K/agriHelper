"""
NLP Pipeline Module
Intent classification and entity extraction using LLM.
Processes transcribed text to understand farmer queries.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Valid intents and entities ────────────────────────────────────────────────
VALID_INTENTS = [
    "weather_query",
    "fertilizer_query",
    "crop_disease_query",
    "market_price_query",
    "government_scheme_query",
    "general_question",
]

VALID_ENTITIES = [
    "crop_name",
    "location",
    "date",
    "disease_name",
    "soil_type",
    "season",
    "fertilizer_name",
]

# ── System prompt for NLP extraction ─────────────────────────────────────────
NLP_SYSTEM_PROMPT = """You are an agricultural NLP assistant. Your job is to analyze farmer queries and extract structured information.

Given a farmer's spoken query (which may be in Tamil, Hindi, or English), you must:

1. **Classify the intent** into EXACTLY ONE of these categories:
   - weather_query: Questions about weather, rainfall, temperature, forecast
   - fertilizer_query: Questions about fertilizers, nutrients, soil treatment
   - crop_disease_query: Questions about crop diseases, pests, plant health issues
   - market_price_query: Questions about crop prices, market rates, selling prices
   - government_scheme_query: Questions about government programs, subsidies, schemes for farmers
   - general_question: Any other agricultural question

2. **Extract entities** from the query. Possible entities:
   - crop_name: Name of the crop (e.g., wheat, rice, sugarcane, tomato)
   - location: Geographic location mentioned (e.g., district, state, village)
   - date: Any date or time period mentioned
   - disease_name: Name of disease or pest
   - soil_type: Type of soil mentioned (e.g., red soil, clay soil, black soil)
   - season: Agricultural season (e.g., kharif, rabi, zaid)
   - fertilizer_name: Specific fertilizer mentioned

IMPORTANT:
- If the query is in Tamil or Hindi, still extract entities in English (transliterate if needed).
- If an entity is not mentioned, do NOT include it.
- Always return valid JSON.

Return your analysis in this EXACT JSON format (no markdown, no explanation):
{
    "intent": "<one of the valid intents>",
    "entities": {
        "crop_name": "<if mentioned>",
        "location": "<if mentioned>",
        "date": "<if mentioned>",
        "disease_name": "<if mentioned>",
        "soil_type": "<if mentioned>",
        "season": "<if mentioned>",
        "fertilizer_name": "<if mentioned>"
    },
    "confidence": <0.0 to 1.0>,
    "query_summary": "<brief English summary of the query>"
}"""


class NLPPipeline:
    """Processes transcribed text through intent classification and entity extraction."""

    def __init__(self, api_key: str, base_url: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def process(self, text: str, language: str = "en") -> dict:
        """
        Process transcribed text to extract intent and entities.

        Args:
            text: Transcribed text from ASR.
            language: Detected language code (ta/hi/en).

        Returns:
            {
                "intent": "weather_query",
                "entities": {"crop_name": "...", "location": "..."},
                "confidence": 0.9,
                "query_summary": "..."
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        logger.info(f"NLP processing: '{text[:80]}...' (lang={language})")
        print(f"🧠 Analyzing query intent and entities...")

        try:
            user_prompt = f"""Analyze this farmer query:

Language: {language}
Query: "{text}"

Extract the intent and entities as specified. Return ONLY valid JSON."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": NLP_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            raw_output = response.choices[0].message.content.strip()
            result = self._parse_llm_output(raw_output)

            logger.info(f"NLP result: intent={result['intent']}, entities={result['entities']}")
            print(f"🎯 Intent: {result['intent']} | Entities: {result['entities']}")
            return result

        except Exception as e:
            logger.error(f"NLP processing failed: {e}")
            return self._fallback_analysis(text, language)

    def _parse_llm_output(self, raw: str) -> dict:
        """Parse and validate LLM JSON output."""
        # Remove markdown code fences if present
        cleaned = raw
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON output: {raw[:200]}")
            return self._empty_result()

        # Validate intent
        intent = parsed.get("intent", "general_question")
        if intent not in VALID_INTENTS:
            intent = "general_question"

        # Clean entities — remove empty values
        raw_entities = parsed.get("entities", {})
        entities = {k: v for k, v in raw_entities.items() if v and k in VALID_ENTITIES}

        return {
            "intent": intent,
            "entities": entities,
            "confidence": parsed.get("confidence", 0.5),
            "query_summary": parsed.get("query_summary", ""),
        }

    def _fallback_analysis(self, text: str, language: str) -> dict:
        """
        Rule-based fallback when LLM is unavailable.
        Uses keyword matching for basic intent classification.
        """
        logger.info("Using fallback rule-based NLP analysis")
        text_lower = text.lower()

        # Keyword-based intent detection
        intent_keywords = {
            "weather_query": [
                "weather", "rain", "rainfall", "temperature", "forecast", "climate",
                "மழை", "வானிலை", "तापमान", "बारिश", "मौसम",
            ],
            "fertilizer_query": [
                "fertilizer", "fertiliser", "nutrient", "urea", "potash", "npk", "manure",
                "உரம்", "उर्वरक", "खाद",
            ],
            "crop_disease_query": [
                "disease", "pest", "insect", "blight", "wilt", "rot", "fungus",
                "நோய்", "பூச்சி", "रोग", "कीट",
            ],
            "market_price_query": [
                "price", "market", "rate", "mandi", "sell", "cost",
                "விலை", "சந்தை", "भाव", "मंडी", "कीमत",
            ],
            "government_scheme_query": [
                "scheme", "subsidy", "government", "pm kisan", "crop insurance",
                "திட்டம்", "மானியம்", "योजना", "सब्सिडी",
            ],
        }

        detected_intent = "general_question"
        for intent, keywords in intent_keywords.items():
            if any(kw in text_lower for kw in keywords):
                detected_intent = intent
                break

        return {
            "intent": detected_intent,
            "entities": {},
            "confidence": 0.3,
            "query_summary": f"Fallback analysis of: {text[:100]}",
        }

    def _empty_result(self) -> dict:
        """Return an empty NLP result."""
        return {
            "intent": "general_question",
            "entities": {},
            "confidence": 0.0,
            "query_summary": "",
        }
