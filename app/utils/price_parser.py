"""
Enhanced Price Parser with Hybrid Architecture (Rule-Based + LLM Fallback).
Supports Arabic and English, budget tolerance, thousands, Arabic digits, and price overrides.
"""

import re
from typing import Optional, Tuple
from app.utils.logger import debug_log
from app.services.llm_price_classifier import LLMPriceClassifier


class PriceParser:
    """
    Comprehensive price parser following all budget understanding rules.
    """

    # Configuration
    BUDGET_TOLERANCE_PERCENT = 10

    # Arabic to Western digit mapping
    ARABIC_DIGITS = {
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }

    # Arabic number words to digits
    ARABIC_NUMBER_WORDS = {
        "صفر": "0",
        "واحد": "1",
        "اثنين": "2",
        "ثلاثة": "3",
        "أربعة": "4",
        "خمسة": "5",
        "ستة": "6",
        "سبعة": "7",
        "ثمانية": "8",
        "تسعة": "9",
        "عشرة": "10",
        "أحد عشر": "11",
        "اثنا عشر": "12",
        "عشرون": "20",
        "ثلاثون": "30",
        "أربعون": "40",
        "خمسون": "50",
        "ستون": "60",
        "سبعون": "70",
        "ثمانون": "80",
        "تسعون": "90",
        "مائة": "100",
        "مائتان": "200",
        "ثلاثمائة": "300",
        "أربعمائة": "400",
        "خمسمائة": "500",
    }

    @staticmethod
    def convert_arabic_digits(text: str) -> str:
        """Convert Arabic digits (٠-٩) to Western digits (0-9)."""
        result = text
        for arabic, western in PriceParser.ARABIC_DIGITS.items():
            result = result.replace(arabic, western)
        return result

    @staticmethod
    def convert_arabic_number_words(text: str) -> str:
        """Convert Arabic number words to digits (basic support)."""
        result = text.lower()
        # Handle thousands expressions
        thousands_patterns = [
            (r"(\d+)\s*آلاف", lambda m: str(int(m.group(1)) * 1000)),
            (r"(\d+)\s*الاف", lambda m: str(int(m.group(1)) * 1000)),
            (r"خمسة\s*آلاف", "5000"),
            (r"عشرة\s*آلاف", "10000"),
            (r"خمسة\s*الاف", "5000"),
            (r"عشرة\s*الاف", "10000"),
        ]
        
        for pattern, replacement in thousands_patterns:
            result = re.sub(pattern, replacement, result)
        
        return result

    @staticmethod
    def normalize_price_text(text: str) -> str:
        """Normalize price text by converting Arabic digits and thousands."""
        # Convert Arabic digits
        normalized = PriceParser.convert_arabic_digits(text)
        # Convert Arabic number words/thousands
        normalized = PriceParser.convert_arabic_number_words(normalized)
        # Convert "k" shorthand
        normalized = re.sub(r"(\d+)\s*[kK]", lambda m: str(int(m.group(1)) * 1000), normalized)
        return normalized

    @staticmethod
    def extract_price(message: str) -> dict:
        """
        Extract price information using Hybrid Architecture (Rule-Based + LLM Fallback).
        
        STEP 1: Run rule-based parsing first.
        STEP 2: If rules fail and message contains numbers, invoke LLM fallback.
        
        Returns dict with min_price, max_price, and price_type.
        """
        debug_log("PRICE_TEXT_DETECTED", message)
        
        # Normalize the message
        normalized = PriceParser.normalize_price_text(message)
        debug_log("PRICE_NORMALIZED", normalized)
        
        result = {
            "min_price": None,
            "max_price": None,
            "price_type": "none",
        }

        # STEP 1: Rule-based parsing
        debug_log("PRICE_RULE_MATCH", "Attempting rule-based classification")
        
        # RULE 5: Explicit range (highest priority)
        range_match = PriceParser._extract_range(normalized)
        if range_match:
            result["min_price"] = range_match[0]
            result["max_price"] = range_match[1]
            result["price_type"] = "range"
            debug_log("PRICE_RULE_MATCH", "Range pattern matched")
            debug_log("PRICE_RANGE_GENERATED", f"{range_match[0]}-{range_match[1]}")
            return result

        # RULE 1 & 2: Budget (exact number or budget phrase) - check before max/min
        budget_match = PriceParser._extract_budget(normalized)
        if budget_match:
            # Apply 10% tolerance
            margin = budget_match * (PriceParser.BUDGET_TOLERANCE_PERCENT / 100)
            min_price = int(budget_match - margin)
            max_price = int(budget_match + margin)
            result["min_price"] = min_price
            result["max_price"] = max_price
            result["price_type"] = "budget"
            debug_log("PRICE_RULE_MATCH", "Budget pattern matched")
            debug_log("PRICE_RANGE_GENERATED", f"{min_price}-{max_price}")
            return result

        # RULE 3: Maximum price
        max_match = PriceParser._extract_max_price(normalized)
        if max_match:
            result["max_price"] = max_match
            result["price_type"] = "max"
            debug_log("PRICE_RULE_MATCH", "Max price pattern matched")
            debug_log("PRICE_RANGE_GENERATED", f"max={max_match}")
            return result

        # RULE 4: Minimum price
        min_match = PriceParser._extract_min_price(normalized)
        if min_match:
            result["min_price"] = min_match
            result["price_type"] = "min"
            debug_log("PRICE_RULE_MATCH", "Min price pattern matched")
            debug_log("PRICE_RANGE_GENERATED", f"min={min_match}")
            return result

        # STEP 2: LLM Fallback
        debug_log("PRICE_RULE_FAILED", "No rule patterns matched")
        
        # Check if message contains numbers
        if LLMPriceClassifier._contains_number(normalized):
            debug_log("PRICE_LLM_FALLBACK", "Invoking LLM fallback classifier")
            
            llm_result = LLMPriceClassifier.classify(normalized)
            
            if llm_result:
                result["min_price"] = llm_result.get("min_price")
                result["max_price"] = llm_result.get("max_price")
                result["price_type"] = llm_result.get("price_intent", "none")
                debug_log("PRICE_OVERRIDE", f"LLM classified as {result['price_type']}")
                debug_log("FINAL_PRICE_FILTERS", f"min={result['min_price']}, max={result['max_price']}")
                return result
            else:
                debug_log("PRICE_LLM_FAILED", "LLM fallback failed or confidence below threshold")
        else:
            debug_log("PRICE_LLM_FAILED", "No numbers in message, skipping LLM fallback")

        debug_log("PRICE_TYPE_DETECTED", "none")
        debug_log("FINAL_PRICE_FILTERS", f"min={result['min_price']}, max={result['max_price']}")
        return result

    @staticmethod
    def _extract_range(text: str) -> Optional[Tuple[int, int]]:
        """Extract explicit price range."""
        patterns = [
            r"من\s*(\d+)\s*لـ?\s*(\d+)",
            r"من\s*(\d+)\s*الى\s*(\d+)",
            r"من\s*(\d+)\s*إلى\s*(\d+)",
            r"بين\s*(\d+)\s*و\s*(\d+)",
            r"between\s+(\d+)\s+and\s+(\d+)",
            r"(\d+)\s*-\s*(\d+)",
            r"(\d+)\s*–\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                min_val = int(match.group(1))
                max_val = int(match.group(2))
                # Ensure min < max
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                return (min_val, max_val)

        return None

    @staticmethod
    def _extract_max_price(text: str) -> Optional[int]:
        """Extract maximum price."""
        patterns = [
            r"تحت\s*(\d+)",
            r"اقل من\s*(\d+)",
            r"أقل من\s*(\d+)",
            r"بحد أقصى\s*(\d+)",
            r"بحد اقصى\s*(\d+)",
            r"maximum\s+(\d+)",
            r"max\s+(\d+)",
            r"up to\s+(\d+)",
            r"لحد\s*(\d+)",
            r"لحاد\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    @staticmethod
    def _extract_min_price(text: str) -> Optional[int]:
        """Extract minimum price."""
        patterns = [
            r"فوق\s*(\d+)",
            r"اكتر من\s*(\d+)",
            r"أكثر من\s*(\d+)",
            r"اكثر من\s*(\d+)",
            r"ازيد من\s*(\d+)",
            r"أزيد من\s*(\d+)",
            r"minimum\s+(\d+)",
            r"min\s+(\d+)",
            r"from\s+(\d+)\s+and\s+above",
            r"من\s+(\d+)\s+فوق",
            r"من\s+(\d+)\s+فوق",
            r"بداية من\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    @staticmethod
    def _extract_budget(text: str) -> Optional[int]:
        """Extract budget (exact number or budget phrase)."""
        # Budget phrases
        budget_patterns = [
            r"ميزانيتي\s*(\d+)",
            r"الميزانية\s*(\d+)",
            r"budget\s*(\d+)",
            r"my budget is\s*(\d+)",
            r"معايا\s*(\d+)",
            r"في حدود\s*(\d+)",
            r"لدي\s*(\d+)",
            r"عندي\s*(\d+)",
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        # Standalone number (treat as budget, not max)
        standalone_pattern = r"^(\d+)$"
        match = re.search(standalone_pattern, text.strip())
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def should_override_price(
        current_min: Optional[int],
        current_max: Optional[int],
        new_min: Optional[int],
        new_max: Optional[int],
    ) -> bool:
        """
        Determine if new price instruction should override old one.
        RULE 8: A new budget instruction replaces old budget instructions.
        """
        # If new instruction has both min and max (range), it overrides
        if new_min is not None and new_max is not None:
            return True

        # If new instruction is a budget (both min and max from tolerance), it overrides
        if new_min is not None and new_max is not None:
            return True

        # If new instruction is max only, and current has min, override
        if new_max is not None and current_min is not None:
            return True

        # If new instruction is min only, and current has max, override
        if new_min is not None and current_max is not None:
            return True

        # Otherwise, merge
        return False

    @staticmethod
    def apply_price_override(
        current_min: Optional[int],
        current_max: Optional[int],
        new_min: Optional[int],
        new_max: Optional[int],
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Apply price override logic.
        Returns (min_price, max_price).
        """
        debug_log("PREVIOUS_PRICE_FILTERS", f"min={current_min}, max={current_max}")

        # Check if we should override
        if PriceParser.should_override_price(current_min, current_max, new_min, new_max):
            debug_log("PRICE_OVERRIDE_DETECTED", "New price instruction overrides old one")
            return (new_min, new_max)

        # Otherwise, merge intelligently
        result_min = new_min if new_min is not None else current_min
        result_max = new_max if new_max is not None else current_max

        debug_log("PRICE_OVERRIDE_DETECTED", "Merging price filters")
        return (result_min, result_max)
