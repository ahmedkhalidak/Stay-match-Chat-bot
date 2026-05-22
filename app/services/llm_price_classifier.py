"""
LLM Fallback Service for Price Classification.
Used when rule-based parsing cannot confidently classify price intent.
"""

import json
import re
from typing import Optional, Dict, Any
from app.utils.logger import debug_log


class LLMPriceClassifier:
    """
    LLM-based price classifier for handling ambiguous or novel phrasings.
    """

    # Confidence threshold for accepting LLM classification
    CONFIDENCE_THRESHOLD = 0.70

    # Budget tolerance percentage
    BUDGET_TOLERANCE_PERCENT = 10

    # System prompt for LLM
    SYSTEM_PROMPT = """You are a price intent classifier for a real estate chatbot in Egypt.
Your task is to analyze user messages and extract price information.

You must return ONLY valid JSON with this exact schema:
{
  "price_intent": "budget|min|max|range|none",
  "min_price": number|null,
  "max_price": number|null,
  "confidence": float
}

Rules:
- "budget": User states their budget/limit (apply 10% tolerance: 5000 → 4500-5500)
- "min": User wants minimum price (e.g., "ازيد من 5000" → min=5000)
- "max": User wants maximum price (e.g., "تحت 5000" → max=5000)
- "range": User specifies a range (e.g., "بين 3000 و 5000" → 3000-5000)
- "none": No price intent detected

Examples:
- "ازيد 5000" → {"price_intent":"min","min_price":5000,"max_price":null,"confidence":0.95}
- "تحت 5000" → {"price_intent":"max","min_price":null,"max_price":5000,"confidence":0.99}
- "في حدود 5000" → {"price_intent":"budget","min_price":4500,"max_price":5500,"confidence":0.95}
- "معايا 5000" → {"price_intent":"budget","min_price":4500,"max_price":5500,"confidence":0.95}
- "بين 3000 و 5000" → {"price_intent":"range","min_price":3000,"max_price":5000,"confidence":0.99}
- "شقة في القاهرة" → {"price_intent":"none","min_price":null,"max_price":null,"confidence":0.90}

Return ONLY JSON. No explanations.
"""

    @staticmethod
    def _extract_numbers(text: str) -> list[int]:
        """Extract all numbers from text."""
        numbers = re.findall(r'\d+', text)
        return [int(n) for n in numbers]

    @staticmethod
    def _contains_number(text: str) -> bool:
        """Check if text contains any numeric value."""
        return bool(re.search(r'\d', text))

    @staticmethod
    def _apply_budget_tolerance(budget: int) -> tuple[int, int]:
        """Apply 10% tolerance to budget."""
        margin = budget * (LLMPriceClassifier.BUDGET_TOLERANCE_PERCENT / 100)
        min_price = int(budget - margin)
        max_price = int(budget + margin)
        return min_price, max_price

    @staticmethod
    def classify(message: str) -> Optional[Dict[str, Any]]:
        """
        Classify price intent using LLM.
        
        Returns None if LLM is not available or confidence is below threshold.
        """
        debug_log("PRICE_LLM_FALLBACK", f"Invoking LLM for: {message}")
        
        # Check if message contains numbers
        if not LLMPriceClassifier._contains_number(message):
            debug_log("PRICE_LLM_FAILED", "No numbers found in message")
            return None

        # TODO: Integrate with actual LLM service
        # For now, use a mock implementation
        result = LLMPriceClassifier._mock_llm_classify(message)
        
        if result is None:
            debug_log("PRICE_LLM_FAILED", "LLM returned None")
            return None

        debug_log("PRICE_LLM_RESPONSE", json.dumps(result, ensure_ascii=False))

        # Check confidence threshold
        if result.get("confidence", 0) < LLMPriceClassifier.CONFIDENCE_THRESHOLD:
            debug_log("PRICE_LLM_FAILED", f"Confidence {result['confidence']} below threshold {LLMPriceClassifier.CONFIDENCE_THRESHOLD}")
            return None

        # Apply budget tolerance if needed
        if result["price_intent"] == "budget" and result["min_price"] is not None:
            numbers = LLMPriceClassifier._extract_numbers(message)
            if numbers:
                budget = numbers[0]  # Use first number as budget
                min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(budget)
                result["min_price"] = min_price
                result["max_price"] = max_price

        return result

    @staticmethod
    def _mock_llm_classify(message: str) -> Optional[Dict[str, Any]]:
        """
        Mock LLM classifier for testing.
        In production, replace with actual LLM API call.
        """
        message_lower = message.lower()
        numbers = LLMPriceClassifier._extract_numbers(message)
        
        if not numbers:
            return {
                "price_intent": "none",
                "min_price": None,
                "max_price": None,
                "confidence": 0.90
            }

        number = numbers[0]

        # Mock classification logic based on patterns
        if any(word in message_lower for word in ["ازيد", "فوق", "اكثر", "اكبر", "أزيد", "فوق"]):
            return {
                "price_intent": "min",
                "min_price": number,
                "max_price": None,
                "confidence": 0.95
            }
        
        if any(word in message_lower for word in ["تحت", "اقل", "أقل", "بحد", "لحد"]):
            return {
                "price_intent": "max",
                "min_price": None,
                "max_price": number,
                "confidence": 0.99
            }
        
        if any(word in message_lower for word in ["بين", "من", "و", "to", "and", "-"]):
            if len(numbers) >= 2:
                return {
                    "price_intent": "range",
                    "min_price": min(numbers),
                    "max_price": max(numbers),
                    "confidence": 0.99
                }
        
        if any(word in message_lower for word in ["معايا", "في حدود", "ميزانيتي", "الميزانية", "budget", "بحوالي", "تقريبا", "حاجة ب"]):
            min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(number)
            return {
                "price_intent": "budget",
                "min_price": min_price,
                "max_price": max_price,
                "confidence": 0.95
            }

        # Default to budget for standalone numbers
        min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(number)
        return {
            "price_intent": "budget",
            "min_price": min_price,
            "max_price": max_price,
            "confidence": 0.85
        }
