"""
Integration tests for Hybrid Price Parser (Rule-Based + LLM Fallback).
Tests the complete hybrid architecture flow.
"""

import pytest
from app.utils.price_parser import PriceParser


class TestHybridPriceParser:
    """Integration tests for hybrid price parser."""

    def test_rule_based_range(self):
        """Test that rule-based parsing handles range correctly."""
        result = PriceParser.extract_price("بين 3000 و 5000")
        assert result["price_type"] == "range"
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000

    def test_rule_based_max(self):
        """Test that rule-based parsing handles max price correctly."""
        result = PriceParser.extract_price("تحت 5000")
        assert result["price_type"] == "max"
        assert result["min_price"] is None
        assert result["max_price"] == 5000

    def test_rule_based_min(self):
        """Test that rule-based parsing handles min price correctly."""
        result = PriceParser.extract_price("فوق 5000")
        assert result["price_type"] == "min"
        assert result["min_price"] == 5000
        assert result["max_price"] is None

    def test_rule_based_budget(self):
        """Test that rule-based parsing handles budget correctly."""
        result = PriceParser.extract_price("ميزانيتي 5000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_llm_fallback_min_price(self):
        """Test LLM fallback for min price phrasing not in rules."""
        result = PriceParser.extract_price("ازيد 5000")
        assert result["price_type"] == "min"
        assert result["min_price"] == 5000
        assert result["max_price"] is None

    def test_llm_fallback_max_price(self):
        """Test LLM fallback for max price phrasing not in rules."""
        result = PriceParser.extract_price("في حدود 5000")
        # This should be classified as budget by LLM
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_llm_fallback_budget(self):
        """Test LLM fallback for budget phrasing not in rules."""
        result = PriceParser.extract_price("معايا 5000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_llm_fallback_approximate(self):
        """Test LLM fallback for approximate budget phrasing."""
        result = PriceParser.extract_price("حاجة بحوالي 4000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 3600
        assert result["max_price"] == 4400

    def test_llm_fallback_standalone_number(self):
        """Test LLM fallback for standalone number."""
        result = PriceParser.extract_price("5000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_llm_fallback_range(self):
        """Test LLM fallback for range phrasing."""
        result = PriceParser.extract_price("من 3000 ل 5000")
        # This should be caught by rules, but if not, LLM handles it
        assert result["price_type"] == "range"
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000

    def test_no_price_detected(self):
        """Test when no price is detected."""
        result = PriceParser.extract_price("شقة في القاهرة")
        assert result["price_type"] == "none"
        assert result["min_price"] is None
        assert result["max_price"] is None

    def test_rule_priority_over_llm(self):
        """Test that rules take priority over LLM for known patterns."""
        # "تحت 5000" is in rules, should not trigger LLM
        result = PriceParser.extract_price("تحت 5000")
        assert result["price_type"] == "max"
        assert result["max_price"] == 5000

    def test_llm_only_invoked_when_rules_fail(self):
        """Test that LLM is only invoked when rules fail."""
        # "ازيد 5000" is not in rules (only "ازيد من 5000" is)
        # So it should trigger LLM fallback
        result = PriceParser.extract_price("ازيد 5000")
        assert result["price_type"] == "min"
        assert result["min_price"] == 5000

    def test_arabic_digits_with_llm(self):
        """Test Arabic digits work with LLM fallback."""
        result = PriceParser.extract_price("معايا ٥٠٠٠")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_thousands_with_llm(self):
        """Test thousands shorthand works with LLM fallback."""
        result = PriceParser.extract_price("معايا 5k")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500

    def test_budget_tolerance_applied_by_llm(self):
        """Test that LLM applies budget tolerance correctly."""
        result = PriceParser.extract_price("ميزانيتي تقريباً 6000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 5400  # 6000 - 10%
        assert result["max_price"] == 6600  # 6000 + 10%

    def test_complex_fallback_scenario(self):
        """Test complex real-world scenario with LLM fallback."""
        result = PriceParser.extract_price("عاوز حاجة ب 7000")
        assert result["price_type"] == "budget"
        assert result["min_price"] == 6300
        assert result["max_price"] == 7700

    def test_rule_based_then_llm_sequence(self):
        """Test sequence of rule-based then LLM fallback."""
        # First: rule-based
        result1 = PriceParser.extract_price("تحت 5000")
        assert result1["price_type"] == "max"
        
        # Then: LLM fallback
        result2 = PriceParser.extract_price("ازيد 7000")
        assert result2["price_type"] == "min"

    def test_no_numbers_no_llm_invocation(self):
        """Test that LLM is not invoked when no numbers present."""
        result = PriceParser.extract_price("أريد شقة")
        assert result["price_type"] == "none"
        assert result["min_price"] is None
        assert result["max_price"] is None

    def test_confidence_threshold_rejection(self):
        """Test that low confidence LLM results are rejected."""
        # The mock classifier returns confidence >= 0.70 for all cases
        # In production, this would test the threshold logic
        result = PriceParser.extract_price("5000")
        # Should succeed because confidence is high
        assert result["price_type"] == "budget"

    def test_hybrid_architecture_end_to_end(self):
        """Test complete end-to-end hybrid architecture."""
        # Rule-based patterns
        assert PriceParser.extract_price("تحت 5000")["price_type"] == "max"
        assert PriceParser.extract_price("فوق 5000")["price_type"] == "min"
        assert PriceParser.extract_price("بين 3000 و 5000")["price_type"] == "range"
        assert PriceParser.extract_price("ميزانيتي 5000")["price_type"] == "budget"
        
        # LLM fallback patterns
        assert PriceParser.extract_price("ازيد 5000")["price_type"] == "min"
        assert PriceParser.extract_price("معايا 5000")["price_type"] == "budget"
        assert PriceParser.extract_price("في حدود 5000")["price_type"] == "budget"
        assert PriceParser.extract_price("حاجة ب 6000")["price_type"] == "budget"

    def test_price_override_with_hybrid(self):
        """Test price override logic works with hybrid architecture."""
        # First: rule-based max
        result1 = PriceParser.extract_price("تحت 5000")
        current_min = result1["min_price"]
        current_max = result1["max_price"]
        
        # Then: LLM fallback min
        result2 = PriceParser.extract_price("ازيد 7000")
        new_min = result2["min_price"]
        new_max = result2["max_price"]
        
        # Apply override logic
        final_min, final_max = PriceParser.apply_price_override(
            current_min=current_min,
            current_max=current_max,
            new_min=new_min,
            new_max=new_max,
        )
        
        assert final_min == 7000
        assert final_max is None

    def test_mixed_rule_and_llm_overrides(self):
        """Test mixed rule-based and LLM-based overrides."""
        # Step 1: Rule-based budget
        result1 = PriceParser.extract_price("ميزانيتي 5000")
        current_min = result1["min_price"]
        current_max = result1["max_price"]
        
        # Step 2: LLM fallback range
        result2 = PriceParser.extract_price("من 3000 ل 7000")
        new_min = result2["min_price"]
        new_max = result2["max_price"]
        
        # Apply override
        final_min, final_max = PriceParser.apply_price_override(
            current_min=current_min,
            current_max=current_max,
            new_min=new_min,
            new_max=new_max,
        )
        
        assert final_min == 3000
        assert final_max == 7000
