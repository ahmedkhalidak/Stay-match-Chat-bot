"""
Integration tests for root search filter reset scenarios.
Tests the complete flow from user message to filter application.
"""

import pytest
from app.core.session_context import SessionContext
from app.models.search_models import SearchFilters
from app.services.conversation_flow import ConversationFlow


class TestFilterResetIntegration:
    """Integration tests for filter reset in conversation flow."""

    def test_shared_student_shared_full_flow(self):
        """Test complete flow: سكن مشترك -> للطلاب -> سكن مشترك"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: User says "سكن مشترك"
        filters1 = SearchFilters(search_type="property", housing_type="shared")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="سكن مشترك")
        
        assert result1.housing_type == "shared"
        assert result1.tenant_type is None
        
        # Simulate user preference being set after first search
        context.user_preferences.tenant_type = "student"
        
        # Step 2: User says "سكن مشترك" again (should trigger reset)
        filters2 = SearchFilters(search_type="property", housing_type="shared")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="سكن مشترك")
        
        # Tenant type should be cleared
        assert result2.housing_type == "shared"
        assert result2.tenant_type is None
        assert context.user_preferences.tenant_type is None

    def test_apartment_furnished_price_apartment_full_flow(self):
        """Test complete flow: شقة كاملة -> مفروشة -> فوق 5000 -> شقة كاملة"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: User says "شقة كاملة"
        filters1 = SearchFilters(search_type="property", housing_type="apartment")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="شقة كاملة")
        
        assert result1.housing_type == "apartment"
        assert result1.furnished is None
        assert result1.min_price is None
        
        # Simulate user preferences being set
        context.user_preferences.furnished = True
        context.user_preferences.min_budget = 5000
        
        # Step 2: User says "شقة كاملة" again (should trigger reset)
        filters2 = SearchFilters(search_type="property", housing_type="apartment")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="شقة كاملة")
        
        # Furnished and price should be cleared
        assert result2.housing_type == "apartment"
        assert result2.furnished is None
        assert result2.min_price is None
        assert context.user_preferences.furnished is None
        assert context.user_preferences.min_budget is None

    def test_room_private_bathroom_room_full_flow(self):
        """Test complete flow: غرفة -> حمام خاص -> غرفة"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: User says "غرفة"
        filters1 = SearchFilters(search_type="property", housing_type="room")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="غرفة")
        
        assert result1.housing_type == "room"
        assert result1.private_bathroom is None
        
        # Simulate user preference being set
        context.user_preferences.private_bathroom = True
        
        # Step 2: User says "غرفة" again (should trigger reset)
        filters2 = SearchFilters(search_type="property", housing_type="room")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="غرفة")
        
        # Private bathroom should be cleared
        assert result2.housing_type == "room"
        assert result2.private_bathroom is None
        assert context.user_preferences.private_bathroom is None

    def test_location_preserved_across_root_search(self):
        """Test that location is preserved when root search is triggered."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set location preference
        context.user_preferences.preferred_location = "Cairo"
        
        # User says "سكن مشترك" with location
        filters = SearchFilters(search_type="property", housing_type="shared")
        result = flow.apply_preferences_to_filters(context, filters, message="سكن مشترك")
        
        # Location should be preserved
        assert result.governorate == "Cairo" or result.city == "Cairo"

    def test_governorate_preserved_across_root_search(self):
        """Test that governorate is preserved when root search is triggered."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set governorate preference
        context.user_preferences.preferred_location = "Cairo"
        
        # User says "شقة كاملة" with governorate
        filters = SearchFilters(search_type="property", housing_type="apartment")
        result = flow.apply_preferences_to_filters(context, filters, message="شقة كاملة")
        
        # Governorate should be preserved
        assert result.governorate == "Cairo"

    def test_no_reset_without_housing_type_keyword(self):
        """Test that reset doesn't trigger without housing type keyword."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.min_budget = 5000
        
        # User says "للطلاب" (no housing type keyword)
        filters = SearchFilters(search_type="property", housing_type="shared")
        result = flow.apply_preferences_to_filters(context, filters, message="للطلاب")
        
        # Preferences should be inherited (no reset)
        assert result.tenant_type == "student"
        assert result.min_price == 5000

    def test_no_reset_without_housing_type_in_filters(self):
        """Test that reset doesn't trigger if housing_type is not in filters."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set preferences
        context.user_preferences.tenant_type = "student"
        
        # User says "سكن مشترك" but housing_type is not in filters
        filters = SearchFilters(search_type="property")
        result = flow.apply_preferences_to_filters(context, filters, message="سكن مشترك")
        
        # Preferences should be inherited (no reset)
        assert result.tenant_type == "student"

    def test_multiple_secondary_filters_reset(self):
        """Test that multiple secondary filters are reset simultaneously."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set multiple preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.gender = "male"
        context.user_preferences.furnished = True
        context.user_preferences.wifi = True
        context.user_preferences.private_bathroom = True
        context.user_preferences.balcony = True
        context.user_preferences.air_conditioning = True
        context.user_preferences.min_budget = 5000
        context.user_preferences.max_budget = 10000
        context.user_preferences.shared_room = True
        
        # User says "غرفة" (should reset all secondary filters)
        filters = SearchFilters(search_type="property", housing_type="room")
        result = flow.apply_preferences_to_filters(context, filters, message="غرفة")
        
        # All secondary filters should be cleared
        assert result.tenant_type is None
        assert result.gender is None
        assert result.furnished is None
        assert result.wifi is None
        assert result.private_bathroom is None
        assert result.balcony is None
        assert result.air_conditioning is None
        assert result.min_price is None
        assert result.max_price is None
        assert result.shared_room is None
        
        # All preferences should be cleared
        assert context.user_preferences.tenant_type is None
        assert context.user_preferences.gender is None
        assert context.user_preferences.furnished is None
        assert context.user_preferences.wifi is None
        assert context.user_preferences.private_bathroom is None
        assert context.user_preferences.balcony is None
        assert context.user_preferences.air_conditioning is None
        assert context.user_preferences.min_budget is None
        assert context.user_preferences.max_budget is None
        assert context.user_preferences.shared_room is None

    def test_root_search_with_different_housing_types(self):
        """Test root search with different housing types."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.furnished = True
        
        # Test with "شقة كاملة"
        filters1 = SearchFilters(search_type="property", housing_type="apartment")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="شقة كاملة")
        assert result1.tenant_type is None
        assert result1.furnished is None
        
        # Reset preferences for next test
        context.user_preferences.tenant_type = "student"
        context.user_preferences.furnished = True
        
        # Test with "غرفة"
        filters2 = SearchFilters(search_type="property", housing_type="room")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="غرفة")
        assert result2.tenant_type is None
        assert result2.furnished is None

    def test_arabic_housing_type_variations(self):
        """Test various Arabic housing type variations."""
        flow = ConversationFlow()
        context = SessionContext()
        
        context.user_preferences.tenant_type = "student"
        
        # Test "شقه مشتركه"
        filters1 = SearchFilters(search_type="property", housing_type="shared")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="شقه مشتركه")
        assert result1.tenant_type is None
        
        # Reset preference
        context.user_preferences.tenant_type = "student"
        
        # Test "غرف"
        filters2 = SearchFilters(search_type="property", housing_type="room")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="غرف")
        assert result2.tenant_type is None

    def test_english_housing_type_keywords(self):
        """Test English housing type keywords."""
        flow = ConversationFlow()
        context = SessionContext()
        
        context.user_preferences.tenant_type = "student"
        
        # Test "room"
        filters1 = SearchFilters(search_type="property", housing_type="room")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="room")
        assert result1.tenant_type is None
        
        # Reset preference
        context.user_preferences.tenant_type = "student"
        
        # Test "rooms"
        filters2 = SearchFilters(search_type="property", housing_type="room")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="rooms")
        assert result2.tenant_type is None

    def test_consecutive_root_searches(self):
        """Test multiple consecutive root searches."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # First root search: "سكن مشترك"
        filters1 = SearchFilters(search_type="property", housing_type="shared")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="سكن مشترك")
        assert result1.tenant_type is None
        
        # Add preference
        context.user_preferences.tenant_type = "student"
        
        # Second root search: "غرفة"
        filters2 = SearchFilters(search_type="property", housing_type="room")
        result2 = flow.apply_preferences_to_filters(context, filters2, message="غرفة")
        assert result2.tenant_type is None
        
        # Add preference again
        context.user_preferences.tenant_type = "student"
        
        # Third root search: "شقة كاملة"
        filters3 = SearchFilters(search_type="property", housing_type="apartment")
        result3 = flow.apply_preferences_to_filters(context, filters3, message="شقة كاملة")
        assert result3.tenant_type is None
