"""
Tests for Enhanced Price Parser.
Tests all budget understanding rules.
"""

import pytest
from app.utils.price_parser import PriceParser


class TestPriceParser:
    """Test suite for PriceParser following all rules."""

    def test_rule1_exact_budget_5000(self):
        """RULE 1: Exact budget 5000 => 4500-5500 (10% tolerance)."""
        result = PriceParser.extract_price("5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule1_exact_budget_8000(self):
        """RULE 1: Exact budget 8000 => 7200-8800 (10% tolerance)."""
        result = PriceParser.extract_price("8000")
        assert result["min_price"] == 7200
        assert result["max_price"] == 8800
        assert result["price_type"] == "budget"

    def test_rule1_exact_budget_12000(self):
        """RULE 1: Exact budget 12000 => 10800-13200 (10% tolerance)."""
        result = PriceParser.extract_price("12000")
        assert result["min_price"] == 10800
        assert result["max_price"] == 13200
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_mizaniati(self):
        """RULE 2: Budget phrase 'ميزانيتي 5000' => 4500-5500."""
        result = PriceParser.extract_price("ميزانيتي 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_al_mizaniya(self):
        """RULE 2: Budget phrase 'الميزانية 5000' => 4500-5500."""
        result = PriceParser.extract_price("الميزانية 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_english(self):
        """RULE 2: Budget phrase 'budget 5000' => 4500-5500."""
        result = PriceParser.extract_price("budget 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_my_budget_is(self):
        """RULE 2: Budget phrase 'my budget is 5000' => 4500-5500."""
        result = PriceParser.extract_price("my budget is 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_maaya(self):
        """RULE 2: Budget phrase 'معايا 5000' => 4500-5500."""
        result = PriceParser.extract_price("معايا 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule2_budget_phrase_fi_hodoud(self):
        """RULE 2: Budget phrase 'في حدود 5000' => 4500-5500."""
        result = PriceParser.extract_price("في حدود 5000")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule3_max_price_taht(self):
        """RULE 3: Max price 'تحت 5000' => max=5000."""
        result = PriceParser.extract_price("تحت 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_aqal_min(self):
        """RULE 3: Max price 'اقل من 5000' => max=5000."""
        result = PriceParser.extract_price("اقل من 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_aqal_min_arabic(self):
        """RULE 3: Max price 'أقل من 5000' => max=5000."""
        result = PriceParser.extract_price("أقل من 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_badd_aqsaa(self):
        """RULE 3: Max price 'بحد أقصى 5000' => max=5000."""
        result = PriceParser.extract_price("بحد أقصى 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_maximum(self):
        """RULE 3: Max price 'maximum 5000' => max=5000."""
        result = PriceParser.extract_price("maximum 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_max(self):
        """RULE 3: Max price 'max 5000' => max=5000."""
        result = PriceParser.extract_price("max 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule3_max_price_up_to(self):
        """RULE 3: Max price 'up to 5000' => max=5000."""
        result = PriceParser.extract_price("up to 5000")
        assert result["min_price"] is None
        assert result["max_price"] == 5000
        assert result["price_type"] == "max"

    def test_rule4_min_price_fawq(self):
        """RULE 4: Min price 'فوق 5000' => min=5000."""
        result = PriceParser.extract_price("فوق 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_akthar_min(self):
        """RULE 4: Min price 'اكثر من 5000' => min=5000."""
        result = PriceParser.extract_price("اكثر من 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_akthar_min_arabic(self):
        """RULE 4: Min price 'أكثر من 5000' => min=5000."""
        result = PriceParser.extract_price("أكثر من 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_azid_min(self):
        """RULE 4: Min price 'ازيد من 5000' => min=5000."""
        result = PriceParser.extract_price("ازيد من 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_azid_min_arabic(self):
        """RULE 4: Min price 'أزيد من 5000' => min=5000."""
        result = PriceParser.extract_price("أزيد من 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_minimum(self):
        """RULE 4: Min price 'minimum 5000' => min=5000."""
        result = PriceParser.extract_price("minimum 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_min(self):
        """RULE 4: Min price 'min 5000' => min=5000."""
        result = PriceParser.extract_price("min 5000")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule4_min_price_from_above(self):
        """RULE 4: Min price 'from 5000 and above' => min=5000."""
        result = PriceParser.extract_price("from 5000 and above")
        assert result["min_price"] == 5000
        assert result["max_price"] is None
        assert result["price_type"] == "min"

    def test_rule5_range_bayn(self):
        """RULE 5: Range 'بين 3000 و 5000' => 3000-5000."""
        result = PriceParser.extract_price("بين 3000 و 5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_arabic_digits(self):
        """RULE 5: Range 'بين ٣٠٠٠ و ٥٠٠٠' => 3000-5000."""
        result = PriceParser.extract_price("بين ٣٠٠٠ و ٥٠٠٠")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_min_ila(self):
        """RULE 5: Range 'من 3000 إلى 5000' => 3000-5000."""
        result = PriceParser.extract_price("من 3000 إلى 5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_min_l(self):
        """RULE 5: Range 'من 3000 ل 5000' => 3000-5000."""
        result = PriceParser.extract_price("من 3000 ل 5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_dash(self):
        """RULE 5: Range '3000-5000' => 3000-5000."""
        result = PriceParser.extract_price("3000-5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_dash_with_spaces(self):
        """RULE 5: Range '3000 - 5000' => 3000-5000."""
        result = PriceParser.extract_price("3000 - 5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule5_range_between_english(self):
        """RULE 5: Range 'between 3000 and 5000' => 3000-5000."""
        result = PriceParser.extract_price("between 3000 and 5000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_rule6_thousands_5k(self):
        """RULE 6: Thousands '5k' => 5000."""
        result = PriceParser.extract_price("5k")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_10k(self):
        """RULE 6: Thousands '10k' => 10000."""
        result = PriceParser.extract_price("10k")
        assert result["min_price"] == 9000
        assert result["max_price"] == 11000
        assert result["price_type"] == "budget"

    def test_rule6_thousands_15k(self):
        """RULE 6: Thousands '15k' => 15000."""
        result = PriceParser.extract_price("15k")
        assert result["min_price"] == 13500
        assert result["max_price"] == 16500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_5_K_uppercase(self):
        """RULE 6: Thousands '5 K' => 5000."""
        result = PriceParser.extract_price("5 K")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_10_K_uppercase(self):
        """RULE 6: Thousands '10 K' => 10000."""
        result = PriceParser.extract_price("10 K")
        assert result["min_price"] == 9000
        assert result["max_price"] == 11000
        assert result["price_type"] == "budget"

    def test_rule6_thousands_5_alaf(self):
        """RULE 6: Thousands '5 الاف' => 5000."""
        result = PriceParser.extract_price("5 الاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_5_alaf_with_space(self):
        """RULE 6: Thousands '5 آلاف' => 5000."""
        result = PriceParser.extract_price("5 آلاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_arabic_digit_5_alaf(self):
        """RULE 6: Thousands '٥ الاف' => 5000."""
        result = PriceParser.extract_price("٥ الاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_arabic_digit_5_alaf_with_space(self):
        """RULE 6: Thousands '٥ آلاف' => 5000."""
        result = PriceParser.extract_price("٥ آلاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_khamsa_alaf(self):
        """RULE 6: Thousands 'خمسة آلاف' => 5000."""
        result = PriceParser.extract_price("خمسة آلاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule6_thousands_ashara_alaf(self):
        """RULE 6: Thousands 'عشرة آلاف' => 10000."""
        result = PriceParser.extract_price("عشرة آلاف")
        assert result["min_price"] == 9000
        assert result["max_price"] == 11000
        assert result["price_type"] == "budget"

    def test_rule7_arabic_digits_5000(self):
        """RULE 7: Arabic digits '٥٠٠٠' => 5000."""
        result = PriceParser.extract_price("٥٠٠٠")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_rule7_arabic_digits_1000(self):
        """RULE 7: Arabic digits '١٠٠٠' => 1000."""
        result = PriceParser.extract_price("١٠٠٠")
        assert result["min_price"] == 900
        assert result["max_price"] == 1100
        assert result["price_type"] == "budget"

    def test_rule7_arabic_digits_2000(self):
        """RULE 7: Arabic digits '٢٠٠٠' => 2000."""
        result = PriceParser.extract_price("٢٠٠٠")
        assert result["min_price"] == 1800
        assert result["max_price"] == 2200
        assert result["price_type"] == "budget"

    def test_rule7_arabic_digits_3000(self):
        """RULE 7: Arabic digits '٣٠٠٠' => 3000."""
        result = PriceParser.extract_price("٣٠٠٠")
        assert result["min_price"] == 2700
        assert result["max_price"] == 3300
        assert result["price_type"] == "budget"

    def test_rule7_arabic_digits_4000(self):
        """RULE 7: Arabic digits '٤٠٠٠' => 4000."""
        result = PriceParser.extract_price("٤٠٠٠")
        assert result["min_price"] == 3600
        assert result["max_price"] == 4400
        assert result["price_type"] == "budget"

    def test_rule8_override_max_then_min(self):
        """RULE 8: Override 'تحت 5000' then 'فوق 5000' => min=5000, max=None."""
        # First: تحت 5000
        result1 = PriceParser.extract_price("تحت 5000")
        current_min = result1["min_price"]
        current_max = result1["max_price"]
        
        # Then: فوق 5000
        result2 = PriceParser.extract_price("فوق 5000")
        new_min = result2["min_price"]
        new_max = result2["max_price"]
        
        # Apply override logic
        final_min, final_max = PriceParser.apply_price_override(
            current_min=current_min,
            current_max=current_max,
            new_min=new_min,
            new_max=new_max,
        )
        
        assert final_min == 5000
        assert final_max is None

    def test_rule8_override_budget_then_range(self):
        """RULE 8: Override 'ميزانيتي 5000' then 'بين 3000 و 7000' => 3000-7000."""
        # First: ميزانيتي 5000
        result1 = PriceParser.extract_price("ميزانيتي 5000")
        current_min = result1["min_price"]
        current_max = result1["max_price"]
        
        # Then: بين 3000 و 7000
        result2 = PriceParser.extract_price("بين 3000 و 7000")
        new_min = result2["min_price"]
        new_max = result2["max_price"]
        
        # Apply override logic
        final_min, final_max = PriceParser.apply_price_override(
            current_min=current_min,
            current_max=current_max,
            new_min=new_min,
            new_max=new_max,
        )
        
        assert final_min == 3000
        assert final_max == 7000

    def test_rule8_override_range_then_max(self):
        """RULE 8: Override range then max should override."""
        # First: بين 3000 و 7000
        result1 = PriceParser.extract_price("بين 3000 و 7000")
        current_min = result1["min_price"]
        current_max = result1["max_price"]
        
        # Then: تحت 5000
        result2 = PriceParser.extract_price("تحت 5000")
        new_min = result2["min_price"]
        new_max = result2["max_price"]
        
        # Apply override logic
        final_min, final_max = PriceParser.apply_price_override(
            current_min=current_min,
            current_max=current_max,
            new_min=new_min,
            new_max=new_max,
        )
        
        assert final_min is None
        assert final_max == 5000

    def test_convert_arabic_digits(self):
        """Test Arabic digit conversion."""
        assert PriceParser.convert_arabic_digits("١٢٣٤٥٦٧٨٩٠") == "1234567890"
        assert PriceParser.convert_arabic_digits("٥٠٠٠") == "5000"
        assert PriceParser.convert_arabic_digits("١٠٠٠") == "1000"

    def test_convert_arabic_number_words(self):
        """Test Arabic number words conversion."""
        assert PriceParser.convert_arabic_number_words("5 آلاف") == "5000"
        assert PriceParser.convert_arabic_number_words("10 آلاف") == "10000"
        assert PriceParser.convert_arabic_number_words("5 الاف") == "5000"
        assert PriceParser.convert_arabic_number_words("خمسة آلاف") == "5000"
        assert PriceParser.convert_arabic_number_words("عشرة آلاف") == "10000"

    def test_normalize_price_text(self):
        """Test price text normalization."""
        assert PriceParser.normalize_price_text("٥٠٠٠") == "5000"
        assert PriceParser.normalize_price_text("5k") == "5000"
        assert PriceParser.normalize_price_text("5 آلاف") == "5000"
        assert PriceParser.normalize_price_text("٥ آلاف") == "5000"

    def test_range_reversed_order(self):
        """Test range with reversed order (5000-3000) should be normalized."""
        result = PriceParser.extract_price("5000-3000")
        assert result["min_price"] == 3000
        assert result["max_price"] == 5000
        assert result["price_type"] == "range"

    def test_no_price_detected(self):
        """Test when no price is detected."""
        result = PriceParser.extract_price("شقة في القاهرة")
        assert result["min_price"] is None
        assert result["max_price"] is None
        assert result["price_type"] == "none"

    def test_budget_tolerance_configurable(self):
        """Test that budget tolerance is configurable."""
        original_tolerance = PriceParser.BUDGET_TOLERANCE_PERCENT
        PriceParser.BUDGET_TOLERANCE_PERCENT = 20
        
        result = PriceParser.extract_price("5000")
        assert result["min_price"] == 4000  # 5000 - 20%
        assert result["max_price"] == 6000  # 5000 + 20%
        
        # Restore original tolerance
        PriceParser.BUDGET_TOLERANCE_PERCENT = original_tolerance
