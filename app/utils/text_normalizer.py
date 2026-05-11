import re

class TextNormalizer:
    """بيحول النص لصيغة موحدة عشان نشتغل عليها"""

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()

        # Arabic normalization
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي",
            "ؤ": "و", "ئ": "ي", "ء": "",
            "ـ": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove repeated chars
        text = re.sub(r"(.)\1+", r"\1", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text
