"""
Integration tests for Price Parser with Conversation Flow.
Tests the complete budget understanding system in context.
"""

import pytest
from app.core.session_context import SessionContext
from app.models.search_models import SearchFilters
from app.services.conversation_flow import ConversationFlow
from app.utils.price_parser import PriceParser


class TestPriceIntegration:
    """Integration tests for price parser with conversation flow."""

    def test_budget_preference_application(self):
        """Test that budget preferences are correctly applied to filters."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set user budget preference
        context.user_preferences.min_budget = 4500
        context.user_preferences.max_budget = 5500
        
        filters = SearchFilters(search_type="property")
        
        # Apply preferences
        result = flow.apply_preferences_to_filters(context, filters)
        
        assert result.min_price == 4500
        assert result.max_price == 5500

    def test_budget_override_with_new_max(self):
        """Test RULE 8: New max overrides old budget."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set initial budget
        context.user_preferences.min_budget = 4500
        context.user_preferences.max_budget = 5500
        
        # User provides new max constraint
        filters = SearchFilters(
            search_type="property",
            min_price=None,
            max_price=7000,
        )
        
        # Apply preferences (should override)
        result = flow.apply_preferences_to_filters(context, filters)
        
        # New max should override old budget
        assert result.max_price == 7000
        # Min should be None (not inherited from old budget)
        assert result.min_price is None

    def test_budget_override_with_new_min(self):
        """Test RULE 8: New min overrides old budget."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set initial budget
        context.user_preferences.min_budget = 4500
        context.user_preferences.max_budget = 5500
        
        # User provides new min constraint
        filters = SearchFilters(
            search_type="property",
            min_price=3000,
            max_price=None,
        )
        
        # Apply preferences (should override)
        result = flow.apply_preferences_to_filters(context, filters)
        
        # New min should override old budget
        assert result.min_price == 3000
        # Max should be None (not inherited from old budget)
        assert result.max_price is None

    def test_budget_override_with_range(self):
        """Test RULE 8: New range overrides old budget."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set initial budget
        context.user_preferences.min_budget = 4500
        context.user_preferences.max_budget = 5500
        
        # User provides new range
        filters = SearchFilters(
            search_type="property",
            min_price=3000,
            max_price=7000,
        )
        
        # Apply preferences (should override)
        result = flow.apply_preferences_to_filters(context, filters)
        
        # New range should override old budget
        assert result.min_price == 3000
        assert result.max_price == 7000

    def test_price_skipped_slot_not_inherited(self):
        """Test that skipped price slot is not inherited from preferences."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set initial budget
        context.user_preferences.min_budget = 4500
        context.user_preferences.max_budget = 5500
        
        # Mark price as skipped
        context.skipped_slots.add("price")
        
        filters = SearchFilters(search_type="property")
        
        # Apply preferences
        result = flow.apply_preferences_to_filters(context, filters)
        
        # Should not inherit from preferences
        assert result.min_price is None
        assert result.max_price is None

    def test_price_override_sequence(self):
        """Test complete price override sequence as per RULE 8 example."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: User says "تحت 5000"
        filters1 = SearchFilters(
            search_type="property",
            min_price=None,
            max_price=5000,
        )
        result1 = flow.apply_preferences_to_filters(context, filters1)
        assert result1.max_price == 5000
        assert result1.min_price is None
        
        # Update preferences
        context.user_preferences.min_budget = result1.min_price
        context.user_preferences.max_budget = result1.max_price
        
        # Step 2: User says "فوق 5000"
        filters2 = SearchFilters(
            search_type="property",
            min_price=5000,
            max_price=None,
        )
        result2 = flow.apply_preferences_to_filters(context, filters2)
        
        # Should override: min=5000, max=None (NOT min=5000, max=5000)
        assert result2.min_price == 5000
        assert result2.max_price is None

    def test_budget_then_range_override(self):
        """Test RULE 8: Budget then range override."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: User says "ميزانيتي 5000"
        filters1 = SearchFilters(
            search_type="property",
            min_price=4500,  # 5000 with 10% tolerance
            max_price=5500,
        )
        result1 = flow.apply_preferences_to_filters(context, filters1)
        assert result1.min_price == 4500
        assert result1.max_price == 5500
        
        # Update preferences
        context.user_preferences.min_budget = result1.min_price
        context.user_preferences.max_budget = result1.max_price
        
        # Step 2: User says "بين 3000 و 7000"
        filters2 = SearchFilters(
            search_type="property",
            min_price=3000,
            max_price=7000,
        )
        result2 = flow.apply_preferences_to_filters(context, filters2)
        
        # Should override: min=3000, max=7000
        assert result2.min_price == 3000
        assert result2.max_price == 7000

    def test_arabic_digit_integration(self):
        """Test Arabic digits work end-to-end."""
        # Parse Arabic digits
        result = PriceParser.extract_price("٥٠٠٠")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_thousands_integration(self):
        """Test thousands shorthand works end-to-end."""
        # Parse "5k"
        result = PriceParser.extract_price("5k")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_arabic_thousands_integration(self):
        """Test Arabic thousands work end-to-end."""
        # Parse "خمسة آلاف"
        result = PriceParser.extract_price("خمسة آلاف")
        assert result["min_price"] == 4500
        assert result["max_price"] == 5500
        assert result["price_type"] == "budget"

    def test_price_sync_with_skipped_slots(self):
        """Test that providing a price reopens a skipped slot."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Mark price as skipped
        context.skipped_slots.add("price")
        
        # User provides a new price
        filters = SearchFilters(
            search_type="property",
            min_price=3000,
            max_price=5000,
        )
        
        # Sync skipped slots
        flow.sync_skipped_slots(context, filters)
        
        # Price should no longer be in skipped slots
        assert "price" not in context.skipped_slots

    def test_no_price_remains_skipped(self):
        """Test that not providing a price keeps slot skipped."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Mark price as skipped
        context.skipped_slots.add("price")
        
        # User provides no price
        filters = SearchFilters(
            search_type="property",
            min_price=None,
            max_price=None,
        )
        
        # Sync skipped slots
        flow.sync_skipped_slots(context, filters)
        
        # Price should remain in skipped slots
        assert "price" in context.skipped_slots

    def test_budget_tolerance_configuration(self):
        """Test that budget tolerance is configurable."""
        original_tolerance = PriceParser.BUDGET_TOLERANCE_PERCENT
        
        # Change tolerance to 20%
        PriceParser.BUDGET_TOLERANCE_PERCENT = 20
        
        result = PriceParser.extract_price("5000")
        assert result["min_price"] == 4000  # 5000 - 20%
        assert result["max_price"] == 6000  # 5000 + 20%
        
        # Restore original tolerance
        PriceParser.BUDGET_TOLERANCE_PERCENT = original_tolerance

    def test_complex_price_scenario(self):
        """Test complex real-world scenario."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # User starts with budget
        filters1 = SearchFilters(
            search_type="property",
            min_price=4500,
            max_price=5500,
        )
        result1 = flow.apply_preferences_to_filters(context, filters1)
        context.user_preferences.min_budget = result1.min_price
        context.user_preferences.max_budget = result1.max_price
        
        # User refines with max
        filters2 = SearchFilters(
            search_type="property",
            min_price=None,
            max_price=5000,
        )
        result2 = flow.apply_preferences_to_filters(context, filters2)
        
        # Should override old budget
        assert result2.max_price == 5000
        assert result2.min_price is None
