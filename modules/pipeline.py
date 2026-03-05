"""
AgriHelper Pipeline Orchestrator
End-to-end pipeline that connects all modules into a unified voice assistant.
"""

import time
import uuid
import json
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AgriHelperPipeline:
    """
    End-to-end pipeline for the Multilingual AI Voice Assistant.

    Pipeline stages:
    1. Audio Input → 2. Preprocessing → 3. STT → 4. NLP →
    5. Knowledge Retrieval → 6. Response Generation → 7. TTS → 8. Playback
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_llm: str = "gemini-2.5-flash",
        model_stt: str = "whisper-1",
        model_tts: str = "gpt-4o-mini-tts",
        db_path: str = "database/agrihelper.db",
        user_id: str = "default_farmer",
    ):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())[:8]

        # Initialize all modules
        from modules.audio_input import AudioRecorder
        from modules.audio_preprocessing import AudioPreprocessor
        from modules.speech_to_text import SpeechToText
        from modules.nlp_pipeline import NLPPipeline
        from modules.response_generator import ResponseGenerator
        from modules.text_to_speech import TextToSpeech
        from modules.audio_playback import AudioPlayer
        from modules.conversation_memory import ConversationMemory
        from modules.knowledge.weather_service import WeatherService
        from modules.knowledge.fertilizer_service import FertilizerService
        from modules.knowledge.market_service import MarketService
        from modules.knowledge.scheme_service import SchemeService

        self.recorder = AudioRecorder()
        self.preprocessor = AudioPreprocessor()
        self.stt = SpeechToText(api_key, base_url, model_stt)
        self.nlp = NLPPipeline(api_key, base_url, model_llm)
        self.response_gen = ResponseGenerator(api_key, base_url, model_llm)
        self.tts = TextToSpeech(api_key, base_url, model_tts)
        self.player = AudioPlayer()
        self.memory = ConversationMemory(db_path)

        # Knowledge services
        self.services = {
            "weather_query": WeatherService(),
            "fertilizer_query": FertilizerService(),
            "market_price_query": MarketService(),
            "government_scheme_query": SchemeService(),
        }

        logger.info(f"Pipeline initialized. Session: {self.session_id}")

    def process_voice_query(
        self,
        audio_path: Optional[str] = None,
        record_duration: Optional[int] = None,
        skip_tts: bool = False,
        skip_playback: bool = False,
    ) -> dict:
        """
        Process a complete voice query through the full pipeline.

        Args:
            audio_path: Path to pre-recorded audio. If None, records from mic.
            record_duration: Recording duration in seconds (if recording).
            skip_tts: Skip text-to-speech generation.
            skip_playback: Skip audio playback.

        Returns:
            Complete pipeline result dict.
        """
        start_time = time.time()
        result = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "success": False,
            "stages": {},
        }

        try:
            # ── Stage 1: Audio Input ─────────────────────────────────────────
            print("\n" + "=" * 60)
            print("🌾 AgriHelper Voice Assistant")
            print("=" * 60)

            if audio_path is None:
                print("\n📍 Stage 1: Recording Audio")
                audio_path = self.recorder.record(
                    output_path="data/input.wav",
                    duration=record_duration,
                )
            else:
                print(f"\n📍 Stage 1: Using pre-recorded audio: {audio_path}")

            result["stages"]["audio_input"] = {"path": audio_path, "status": "complete"}

            # ── Stage 2: Preprocessing ───────────────────────────────────────
            print("\n📍 Stage 2: Preprocessing Audio")
            processed_path = self.preprocessor.preprocess(
                audio_path, output_path="data/processed.wav"
            )
            result["stages"]["preprocessing"] = {"path": processed_path, "status": "complete"}

            # ── Stage 3: Speech-to-Text ──────────────────────────────────────
            print("\n📍 Stage 3: Speech-to-Text (ASR)")
            stt_result = self.stt.transcribe_with_retry(processed_path)

            if "error" in stt_result:
                raise RuntimeError(f"ASR failed: {stt_result['error']}")

            language = stt_result["language"]
            spoken_text = stt_result["text"]
            result["stages"]["stt"] = stt_result

            if not spoken_text.strip():
                raise RuntimeError("No speech detected in audio")

            # ── Stage 4: NLP Processing ──────────────────────────────────────
            print("\n📍 Stage 4: NLP Processing (Intent & Entity Extraction)")
            nlp_result = self.nlp.process(spoken_text, language)
            intent = nlp_result["intent"]
            entities = nlp_result["entities"]
            result["stages"]["nlp"] = nlp_result

            # ── Stage 5: Knowledge Retrieval ─────────────────────────────────
            print("\n📍 Stage 5: Knowledge Retrieval")
            knowledge_data = self._retrieve_knowledge(intent, entities)
            result["stages"]["knowledge"] = knowledge_data

            # ── Stage 6: Response Generation ─────────────────────────────────
            print("\n📍 Stage 6: Response Generation")
            response_text = self.response_gen.generate(
                intent=intent,
                entities=entities,
                knowledge_data=knowledge_data,
                language=language,
                original_query=spoken_text,
            )
            result["stages"]["response"] = {"text": response_text, "language": language}

            print(f"\n{'─' * 50}")
            print(f"📋 Response ({language.upper()}):")
            print(f"{'─' * 50}")
            print(response_text)
            print(f"{'─' * 50}")

            # ── Stage 7: Text-to-Speech ──────────────────────────────────────
            audio_output_path = None
            if not skip_tts:
                print("\n📍 Stage 7: Text-to-Speech")
                audio_output_path = self.tts.synthesize(
                    text=response_text,
                    language=language,
                    output_path="data/response.wav",
                )
                result["stages"]["tts"] = {"path": audio_output_path, "status": "complete"}

                # ── Stage 8: Audio Playback ──────────────────────────────────
                if not skip_playback:
                    print("\n📍 Stage 8: Audio Playback")
                    self.player.play_in_notebook(audio_output_path)
                    result["stages"]["playback"] = {"status": "complete"}

            # ── Record success ───────────────────────────────────────────────
            processing_time = round(time.time() - start_time, 2)
            result["success"] = True
            result["processing_time_sec"] = processing_time

            # ── Stage 9: Save to Memory ──────────────────────────────────────
            conv_id = self.memory.save_conversation(
                user_id=self.user_id,
                session_id=self.session_id,
                language=language,
                spoken_text=spoken_text,
                intent=intent,
                entities=entities,
                knowledge_data=knowledge_data,
                response_text=response_text,
                audio_input=audio_path,
                audio_output=audio_output_path,
                processing_time=processing_time,
            )
            result["conversation_id"] = conv_id

            print(f"\n✅ Query processed in {processing_time}s (ID: {conv_id})")
            print("=" * 60)

        except Exception as e:
            processing_time = round(time.time() - start_time, 2)
            result["error"] = str(e)
            result["processing_time_sec"] = processing_time

            logger.error(f"Pipeline error: {e}")
            print(f"\n❌ Error: {e}")

            # Save failed conversation
            self.memory.save_conversation(
                user_id=self.user_id,
                session_id=self.session_id,
                language="en",
                spoken_text=result.get("stages", {}).get("stt", {}).get("text", ""),
                intent="error",
                entities={},
                knowledge_data={},
                response_text="",
                processing_time=processing_time,
                success=False,
                error_message=str(e),
            )

        return result

    def process_text_query(
        self,
        text: str,
        language: str = "en",
        skip_tts: bool = False,
        skip_playback: bool = False,
    ) -> dict:
        """
        Process a text query (skipping audio input and STT).
        Useful for testing and text-based interaction.

        Args:
            text: The query text.
            language: Language code ('en', 'ta', 'hi').
            skip_tts: Skip text-to-speech.
            skip_playback: Skip playback.

        Returns:
            Pipeline result dict.
        """
        start_time = time.time()
        result = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "success": False,
            "stages": {},
        }

        try:
            print("\n" + "=" * 60)
            print("🌾 AgriHelper — Text Query Mode")
            print("=" * 60)
            print(f"📝 Query: {text}")
            print(f"🌐 Language: {language}")

            # ── NLP Processing ───────────────────────────────────────────────
            print("\n📍 NLP Processing")
            nlp_result = self.nlp.process(text, language)
            intent = nlp_result["intent"]
            entities = nlp_result["entities"]
            result["stages"]["nlp"] = nlp_result

            # ── Knowledge Retrieval ──────────────────────────────────────────
            print("\n📍 Knowledge Retrieval")
            knowledge_data = self._retrieve_knowledge(intent, entities)
            result["stages"]["knowledge"] = knowledge_data

            # ── Response Generation ──────────────────────────────────────────
            print("\n📍 Response Generation")
            response_text = self.response_gen.generate(
                intent=intent,
                entities=entities,
                knowledge_data=knowledge_data,
                language=language,
                original_query=text,
            )
            result["stages"]["response"] = {"text": response_text, "language": language}

            print(f"\n{'─' * 50}")
            print(f"📋 Response ({language.upper()}):")
            print(f"{'─' * 50}")
            print(response_text)
            print(f"{'─' * 50}")

            # ── TTS ──────────────────────────────────────────────────────────
            audio_output_path = None
            if not skip_tts:
                print("\n📍 Text-to-Speech")
                audio_output_path = self.tts.synthesize(
                    text=response_text,
                    language=language,
                    output_path="data/response.wav",
                )
                result["stages"]["tts"] = {"path": audio_output_path}

                if not skip_playback:
                    self.player.play_in_notebook(audio_output_path)

            processing_time = round(time.time() - start_time, 2)
            result["success"] = True
            result["processing_time_sec"] = processing_time

            conv_id = self.memory.save_conversation(
                user_id=self.user_id,
                session_id=self.session_id,
                language=language,
                spoken_text=text,
                intent=intent,
                entities=entities,
                knowledge_data=knowledge_data,
                response_text=response_text,
                audio_output=audio_output_path,
                processing_time=processing_time,
            )
            result["conversation_id"] = conv_id

            print(f"\n✅ Processed in {processing_time}s")

        except Exception as e:
            result["error"] = str(e)
            result["processing_time_sec"] = round(time.time() - start_time, 2)
            logger.error(f"Text pipeline error: {e}")
            print(f"\n❌ Error: {e}")

        return result

    def _retrieve_knowledge(self, intent: str, entities: dict) -> dict:
        """Route to the appropriate knowledge service based on intent."""
        logger.info(f"Retrieving knowledge: intent={intent}, entities={entities}")

        try:
            if intent == "weather_query":
                service = self.services["weather_query"]
                return service.get_weather(
                    location=entities.get("location"),
                    date=entities.get("date"),
                )

            elif intent == "fertilizer_query":
                service = self.services["fertilizer_query"]
                return service.get_recommendation(
                    crop_name=entities.get("crop_name"),
                    soil_type=entities.get("soil_type"),
                    location=entities.get("location"),
                )

            elif intent == "market_price_query":
                service = self.services["market_price_query"]
                return service.get_prices(
                    crop_name=entities.get("crop_name"),
                    location=entities.get("location"),
                )

            elif intent == "government_scheme_query":
                service = self.services["government_scheme_query"]
                return service.search_schemes(
                    query=entities.get("crop_name", ""),
                    category=None,
                    location=entities.get("location"),
                )

            elif intent == "crop_disease_query":
                # Use LLM for disease guidance (no specific dataset)
                return {
                    "type": "crop_disease_guidance",
                    "crop": entities.get("crop_name", "unknown"),
                    "disease": entities.get("disease_name", "unknown"),
                    "note": "Detailed disease identification requires visual inspection. General guidance provided.",
                }

            else:
                return {
                    "type": "general_knowledge",
                    "note": "General agricultural question — LLM will provide best response.",
                }

        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return {
                "error": f"Knowledge retrieval failed: {str(e)}",
                "fallback": True,
            }

    def get_history(self, limit: int = 10) -> list:
        """Get conversation history for the current user."""
        return self.memory.get_conversation_history(self.user_id, limit)

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return self.memory.get_stats(self.user_id)
