import random
import asyncio
import google.generativeai as genai
from app.core.config import settings
from app.utils.bilingual_responses import t
from app.utils.language_detector import detect_language
from app.utils.logger import debug_log


class ChatService:
    _model = None

    @classmethod
    def _get_gemini_model(cls):
        """Lazy classmethod caching for Gemini model."""
        if cls._model is None and settings.gemini_api_key:
            debug_log("GEMINI", f"Initializing Gemini model with API key: {settings.gemini_api_key[:10]}...")
            genai.configure(api_key=settings.gemini_api_key)
            cls._model = genai.GenerativeModel('gemini-2.5-flash-lite')
            debug_log("GEMINI", "Gemini model initialized successfully")
        elif cls._model is None:
            debug_log("GEMINI", "Gemini API key not found in settings")
        return cls._model

    async def generate_reply(self, message: str, lang: str = "ar") -> str:
        """Generate small talk reply using Gemini API with StayMatch identity."""
        model = self._get_gemini_model()
        
        if not model:
            debug_log("GEMINI", "Model not available, using fallback")
            # Fallback to simple responses if Gemini is not configured
            return self._fallback_reply(message, lang)
        
        category = self._detect_category(message)
        debug_log("GEMINI", f"Using Gemini for message: {message[:50]}, category: {category}, lang: {lang}")
        
        system_prompt = (
            "You are StayMatch's friendly in-app assistant.\n\n"
            "StayMatch is an Egyptian platform that helps people find compatible roommates, rooms, and apartments based on lifestyle, budget, preferences, and location.\n\n"
            "Your role is to handle greetings, small talk, onboarding conversations, and simple user engagement inside the StayMatch app.\n\n"
            "Rules:\n\n"
            "* Always speak as the StayMatch assistant.\n"
            "* Always write the brand name exactly as \"StayMatch\".\n"
            f"* Reply in the same language as the user's message (lang={lang}).\n"
            "* Keep responses short, natural, warm, and conversational.\n"
            "* Use only 1–2 sentences.\n"
            "* Vary your wording and tone to avoid repetitive responses.\n"
            "* Sometimes greet the user.\n"
            "* Sometimes offer assistance.\n"
            "* Sometimes simply acknowledge the message warmly.\n"
            "* Do not always end with a question.\n"
            "* Sound human, friendly, and welcoming rather than robotic.\n\n"
            "Scope:\n\n"
            "* Stay focused on housing, roommates, apartment searching, moving, and the StayMatch experience.\n"
            "* For messages unrelated to StayMatch, politely redirect the conversation toward how StayMatch can help with finding housing or roommates.\n"
            "* Never claim to perform actions, searches, bookings, or recommendations that are not available in the current context.\n"
            "* Never invent property listings, prices, locations, users, or roommate matches.\n"
            "* Never discuss politics, religion, medical advice, legal advice, coding, or general knowledge topics.\n\n"
            "Examples of good responses:\n\n"
            "* \"Welcome to StayMatch! Happy to help you find the right place.\"\n"
            "* \"Glad you're here. Let's make your housing search easier.\"\n"
            "* \"Hi! StayMatch is ready to help you find a compatible roommate.\"\n"
            "* \"Welcome back to StayMatch. What would you like help with today?\"\n"
            "* \"Happy to see you here! Let's find a place that fits your lifestyle.\"\n\n"
            f"Category: {category}"
        )
        
        try:
            response = await asyncio.to_thread(
                model.generate_content,
                f"{system_prompt}\n\nUser: {message}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,
                    top_p=0.95,
                    max_output_tokens=100,
                )
            )
            reply = response.text.strip()
            debug_log("GEMINI", f"Gemini response: {reply[:100]}")
            return reply
        except Exception as e:
            debug_log("GEMINI", f"Error calling Gemini: {str(e)}")
            # Fallback to simple responses on error
            return self._fallback_reply(message, lang)

    def _detect_category(self, message: str) -> str:
        """Detect the category of the small talk message."""
        text = message.lower().strip()
        
        greeting_words = [
            "عامل", "اخبارك", "ازيك", "عامل اي", "عامل ايه", "اهلا", "هاي", "هلو",
            "hello", "hi", "hey", "good morning", "good evening",
            "how are you", "how's it going", "morning", "evening",
            "مرحبا", "السلام عليكم",
        ]
        thanks_words = [
            "شكرا", "شكر", "ميرسي", "مرسي", "ثانكس", "متشكر",
            "متشكرين", "تسلم", "تسلملي", "حبيبي", "شكراااا",
            "thanks", "thank you", "thx", "thank u", "thanks a lot",
            "appreciate it", "much appreciated",
        ]
        bye_words = [
            "سلام", "باي", "اشوفك", "مع السلامه", "مع السلامة",
            "bye", "goodbye", "see you", "see ya", "later",
            "مع_السلامه",
        ]

        for word in greeting_words:
            if word in text:
                return "greeting"
        for word in thanks_words:
            if word in text:
                return "thanks"
        for word in bye_words:
            if word in text:
                return "bye"
        
        return "general"

    def _fallback_reply(self, message: str, lang: str) -> str:
        """Fallback to simple responses when Gemini is not available."""
        text = message.lower().strip()
        category = self._detect_category(message)
        
        if category == "greeting":
            return random.choice(t("GREETING_REPLIES", lang))
        elif category == "thanks":
            return random.choice(t("THANKS_REPLIES", lang))
        elif category == "bye":
            return random.choice(t("BYE_REPLIES", lang))
        
        return "😄"