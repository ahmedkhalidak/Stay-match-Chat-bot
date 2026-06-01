import random

from app.utils.bilingual_responses import t
from app.utils.language_detector import detect_language


class ChatService:

    def generate_reply(self, message: str, lang: str = "ar") -> str:
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
                return random.choice(t("GREETING_REPLIES", lang))

        for word in thanks_words:
            if word in text:
                return random.choice(t("THANKS_REPLIES", lang))

        for word in bye_words:
            if word in text:
                return random.choice(t("BYE_REPLIES", lang))

        return "😄"