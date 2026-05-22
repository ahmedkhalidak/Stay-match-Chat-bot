"""
Unit tests for LLM Price Classifier.
Tests the LLM fallback service for price classification.
"""

import pytest
from app.services.llm_price_classifier import LLMPriceClassifier


class TestLLMPriceClassifier:
    """Test suite for LLM Price Classifier."""

    def test_contains_number_true(self):
        """Test _contains_number returns True for numeric text."""
        assert LLMPriceClassifier._contains_number("5000") is True
        assert LLMPriceClassifier._contains_number("ازيد 5000") is True
        assert LLMPriceClassifier._contains_number("حاجة ب 6000") is True

    def test_contains_number_false(self):
        """Test _contains_number returns False for non-numeric text."""
        assert LLMPriceClassifier._contains_number("شقة في القاهرة") is False
        assert LLMPriceClassifier._contains_number("أريد شقة") is False
        assert LLMPriceClassifier._contains_number("معايا") is False

    def test_extract_numbers(self):
        """Test _extract_numbers extracts all numbers."""
        assert LLMPriceClassifier._extract_numbers("5000") == [5000]
        assert LLMPriceClassifier._extract_numbers("ازيد 5000") == [5000]
        assert LLMPriceClassifier._extract_numbers("بين 3000 و 5000") == [3000, 5000]
        assert LLMPriceClassifier._extract_numbers("حاجة ب 6000") == [6000]

    def test_apply_budget_tolerance(self):
        """Test _apply_budget_tolerance applies 10% margin."""
        min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(5000)
        assert min_price == 4500
        assert max_price == 5500

    def test_apply_budget_tolerance_3000(self):
        """Test _apply_budget_tolerance with 3000."""
        min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(3000)
        assert min_price == 2700
        assert max_price == 3300

    def test_apply_budget_tolerance_10000(self):
        """Test _apply_budget_tolerance with 10000."""
        min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(10000)
        assert min_price == 9000
        assert max_price == 11000

    def test_classify_min_price(self):
        """Test classify for min price intent."""
        result = LLMPriceClassifier.classify("ازيد 5000")
        assert result is not None
        assert result["price_intent"] == "min"
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["confidence"] >= 0.70

    def test_classify_min_price_variations(self):
        """Test classify for min price intent with variations."""
        result1 = LLMPriceClassifier.classify("فوق 5000")
        assert result1["price_intent"] == "min"
        
        result2 = LLMPriceClassifier.classify("اكثر من 5000")
        assert result2["price_intent"] == "min"

    def test_classify_max_price(self):
        """Test classify for max price intent."""
        result = LLMPriceClassifier.classify("تحت 5000")
        assert result is not None
        assert result["price_intent"] == "max"
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["confidence"] >= 0.70

    def test_classify_max_price_variations(self):
        """Test classify for max price intent with variations."""
        result1 = LLMPriceClassifier.classify("اقل من 5000")
        assert result1["price_intent"] == "max"
        
        result2 = LLMPriceClassifier.classify("أقل من 5000")
        assert result2["price_intent"] == "max"

    def test_classify_budget(self):
        """Test classify for budget intent."""
        result = LLMPriceClassifier.classify("في حدود 5000")
        assert result is not None
        assert result["price_intent"] == "budget"
        assert result["min_price"] == 4500  # 10% tolerance
        assert result["max_price"] == 5500  # 10% tolerance
        assert result["confidence"] >= 0.70

    def test_classify_budget_variations(self):
        """Test classify for budget intent with variations."""
        result1 = LLMPriceClassifier.classify("معايا 5000")
        assert result1["price_intent"] == "budget"
        assert result1["min_price"] == 4500
        assert result1["max_price"] == 5500
        
        result2 = LLMPriceClassifier.classify("ميزانيتي 5000")
        assert result2["price_intent"] == "budget"
        
        result3 = LLMPriceClassifier.classify("بحوالي 5000")
        assert result3["price_intent"] == "budget"
        
        result4 = LLMPriceClassifier.classify("حاجة ب 6000")
        assert result4["price_intent"] == "budget"

    def test_classify_range(self):
        """Test classify for range intent."""
        result = LLMPriceClassifier.classify("بين 3000 و 5000")
        assert result is not None
        assert result["price_intent"] == "range"
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["confidence"] >= 0.70

    def test_classify_range_variations(self):
        """Test classify for range intent with variations."""
        result1 = LLMPriceClassifier.classify("من 3000 ل 5000")
        assert result1["price_intent"] == "range"
        
        result2 = LLMPriceClassifier.classify("3000-5000")
        assert result2["price_intent"] == "range"

    def test_classify_none(self):
        """Test classify returns None when no numbers present."""
        result = LLMPriceClassifier.classify("شقة في القاهرة")
        assert result is None  # Returns None when no numbers found

    def test_classify_no_numbers(self):
        """Test classify returns None when no numbers present."""
        result = LLMPriceClassifier.classify("أريد شقة")
        assert result is None

    def test_classify_standalone_number(self):
        """Test classify for standalone number (default to budget)."""
        result = LLMPriceClassifier.classify("5000")
        assert result is not None
        assert result["price_intent"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_classify_approximate_budget(self):
        """Test classify for approximate budget phrases."""
        result = LLMPriceClassifier.classify("ميزانيتي تقريباً 6000")
        assert result is not None
        assert result["price_intent"] == "budget"
        assert result["min_price"] == 5400  # 6000 - 10%
        assert result["max_price"] == 6600  # 6000 + 10%

    def test_confidence_threshold(self):
        """Test that low confidence results are rejected."""
        # The mock classifier always returns confidence >= 0.70
        # In production, this would test the threshold logic
        result = LLMPriceClassifier.classify("5000")
        if result:
            assert result["confidence"] >= LLMPriceClassifier.CONFIDENCE_THRESHOLD

    def test_confidence_threshold_configurable(self):
        """Test that confidence threshold is configurable."""
        original_threshold = LLMPriceClassifier.CONFIDENCE_THRESHOLD
        LLMPriceClassifier.CONFIDENCE_THRESHOLD = 0.90
        
        result = LLMPriceClassifier.classify("5000")
        # Mock classifier returns 0.85 for standalone numbers
        # With threshold 0.90, this should return None
        # But our mock returns 0.85, so let's test the logic
        assert result is None or result["confidence"] >= 0.90
        
        # Restore original threshold
        LLMPriceClassifier.CONFIDENCE_THRESHOLD = original_threshold

    def test_budget_tolerance_configurable(self):
        """Test that budget tolerance is configurable."""
        original_tolerance = LLMPriceClassifier.BUDGET_TOLERANCE_PERCENT
        LLMPriceClassifier.BUDGET_TOLERANCE_PERCENT = 20
        
        min_price, max_price = LLMPriceClassifier._apply_budget_tolerance(5000)
        assert min_price == 4000  # 5000 - 20%
        assert max_price == 6000  # 5000 + 20%
        
        # Restore original tolerance
        LLMPriceClassifier.BUDGET_TOLERANCE_PERCENT = original_tolerance

    def test_classify_arabic_digits(self):
        """Test classify handles Arabic digits."""
        result = LLMPriceClassifier.classify("معايا ٥٠٠٠")
        assert result is not None
        assert result["price_intent"] == "budget"
        # Arabic digits should be converted by normalization before classification

    def test_classify_thousands(self):
        """Test classify handles thousands shorthand."""
        result = LLMPriceClassifier.classify("معايا 5k")
        assert result is not None
        assert result["price_intent"] == "budget"
        # Thousands should be converted by normalization before classification
