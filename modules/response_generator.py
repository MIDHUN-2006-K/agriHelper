"""
Response Generator Module
Converts structured knowledge data into natural language responses
in the farmer's detected language (Tamil, Hindi, or English).
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Language-specific response templates (fallback) ──────────────────────────
LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in clear, simple English suitable for a farmer.",
    "ta": "Respond ENTIRELY in Tamil (தமிழ்). Use Tamil script only. Keep it simple and farmer-friendly.",
    "hi": "Respond ENTIRELY in Hindi (हिन्दी). Use Devanagari script only. Keep it simple and farmer-friendly.",
}

RESPONSE_SYSTEM_PROMPT = """You are an agricultural expert assistant helping Indian farmers.
Your role is to convert structured agricultural data into helpful, easy-to-understand natural language responses.

Guidelines:
1. Use simple, farmer-friendly language — avoid technical jargon.
2. Be concise but complete — include key facts and actionable advice.
3. If data includes numbers (prices, quantities), present them clearly.
4. Add practical tips where appropriate.
5. Be encouraging and supportive in tone.
6. IMPORTANT: Respond ONLY in the language specified. Do NOT mix languages.
7. Structure the response with clear points if multiple pieces of information.
8. Keep response under 200 words.
"""

# ── Error/fallback responses per language ────────────────────────────────────
FALLBACK_RESPONSES = {
    "en": {
        "api_error": "I'm sorry, I couldn't process your request right now. Please try again in a moment.",
        "no_data": "I don't have information about that right now. Please try a different question.",
        "general": "Thank you for your question. Unfortunately, I'm having trouble generating a response. Please try again.",
    },
    "ta": {
        "api_error": "மன்னிக்கவும், உங்கள் கோரிக்கையை இப்போது செயல்படுத்த முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
        "no_data": "இதை பற்றிய தகவல் இப்போது கிடைக்கவில்லை. வேறு கேள்வியைக் கேளுங்கள்.",
        "general": "உங்கள் கேள்விக்கு நன்றி. பதில் உருவாக்குவதில் சிக்கல் உள்ளது. மீண்டும் முயற்சிக்கவும்.",
    },
    "hi": {
        "api_error": "क्षमा करें, अभी आपका अनुरोध संसाधित नहीं हो सका। कृपया कुछ देर बाद पुनः प्रयास करें।",
        "no_data": "इसके बारे में अभी जानकारी उपलब्ध नहीं है। कृपया कोई दूसरा प्रश्न पूछें।",
        "general": "आपके प्रश्न के लिए धन्यवाद। उत्तर बनाने में समस्या हो रही है। कृपया पुनः प्रयास करें।",
    },
}


class ResponseGenerator:
    """Generates natural language responses from structured data using LLM."""

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

    def generate(
        self,
        intent: str,
        entities: dict,
        knowledge_data: dict,
        language: str = "en",
        original_query: str = "",
    ) -> str:
        """
        Generate a natural language response.

        Args:
            intent: Classified intent (e.g., 'weather_query').
            entities: Extracted entities dict.
            knowledge_data: Structured data from knowledge services.
            language: Target response language ('ta', 'hi', 'en').
            original_query: Original farmer query text.

        Returns:
            Natural language response string.
        """
        logger.info(f"Generating response: intent={intent}, lang={language}")
        print(f"💬 Generating {LANGUAGE_INSTRUCTIONS.get(language, 'English')} response...")

        try:
            lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])

            user_prompt = f"""{lang_instruction}

Farmer's original query: "{original_query}"

Intent: {intent}
Entities detected: {json.dumps(entities, ensure_ascii=False)}

Data retrieved:
{json.dumps(knowledge_data, ensure_ascii=False, indent=2)}

Generate a helpful, natural response for the farmer based on the above data.
Remember: Respond ONLY in {'Tamil (தமிழ்)' if language == 'ta' else 'Hindi (हिन्दी)' if language == 'hi' else 'English'}."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=600,
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Response generated: {result[:100]}...")
            return result

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self._get_fallback(language, "api_error")

    def generate_error_response(self, error_type: str, language: str = "en") -> str:
        """Generate an error response in the appropriate language."""
        return self._get_fallback(language, error_type)

    def _get_fallback(self, language: str, error_type: str) -> str:
        """Get a fallback response for the given language and error type."""
        lang_responses = FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"])
        return lang_responses.get(error_type, lang_responses["general"])
