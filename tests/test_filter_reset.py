"""
Unit tests for filter reset logic when housing type is explicitly provided.
Tests the root search detection and filter reset functionality.
"""

import pytest
from app.core.session_context import SessionContext
from app.models.search_models import SearchFilters
from app.services.conversation_flow import ConversationFlow


class TestFilterReset:
    """Test suite for filter reset logic."""

    def test_is_root_search_housing_type_shared(self):
        """Test detection of shared housing keyword."""
        assert ConversationFlow._is_root_search_housing_type("سكن مشترك") is True
        assert ConversationFlow._is_root_search_housing_type("شقة مشتركة") is True
        assert ConversationFlow._is_root_search_housing_type("مشترك") is True

    def test_is_root_search_housing_type_apartment(self):
        """Test detection of apartment keyword."""
        assert ConversationFlow._is_root_search_housing_type("شقة كاملة") is True
        assert ConversationFlow._is_root_search_housing_type("شقة") is True
        assert ConversationFlow._is_root_search_housing_type("كاملة") is True

    def test_is_root_search_housing_type_room(self):
        """Test detection of room keyword."""
        assert ConversationFlow._is_root_search_housing_type("غرفة") is True
        assert ConversationFlow._is_root_search_housing_type("غرف") is True
        assert ConversationFlow._is_root_search_housing_type("اوضة") is True
        assert ConversationFlow._is_root_search_housing_type("room") is True

    def test_is_root_search_housing_type_false(self):
        """Test that non-housing keywords return False."""
        assert ConversationFlow._is_root_search_housing_type("للطلاب") is False
        assert ConversationFlow._is_root_search_housing_type("مفروشة") is False
        assert ConversationFlow._is_root_search_housing_type("تحت 5000") is False
        assert ConversationFlow._is_root_search_housing_type("في القاهرة") is False

    def test_reset_secondary_filters_all(self):
        """Test that all secondary filters are reset."""
        filters = SearchFilters(
            housing_type="shared",
            tenant_type="student",
            gender="male",
            furnished=True,
            wifi=True,
            private_bathroom=True,
            balcony=True,
            air_conditioning=True,
            min_price=5000,
            max_price=10000,
            sort_by="price_low",
            shared_room=True,
            city="Cairo",
        )
        
        result = ConversationFlow._reset_secondary_filters(filters, preserve_location=True)
        
        assert result.housing_type == "shared"  # Preserved
        assert result.tenant_type is None
        assert result.gender is None
        assert result.furnished is None
        assert result.wifi is None
        assert result.private_bathroom is None
        assert result.balcony is None
        assert result.air_conditioning is None
        assert result.min_price is None
        assert result.max_price is None
        assert result.sort_by is None
        assert result.shared_room is None
        assert result.city == "Cairo"  # Preserved

    def test_reset_secondary_filters_preserve_governorate(self):
        """Test that governorate is preserved when preserve_location=True."""
        filters = SearchFilters(
            housing_type="shared",
            tenant_type="student",
            governorate="Cairo",
        )
        
        result = ConversationFlow._reset_secondary_filters(filters, preserve_location=True)
        
        assert result.governorate == "Cairo"  # Preserved
        assert result.tenant_type is None

    def test_apply_preferences_with_root_search(self):
        """Test that root search triggers filter reset."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set up preferences with secondary filters
        context.user_preferences.tenant_type = "student"
        context.user_preferences.gender = "male"
        context.user_preferences.furnished = True
        context.user_preferences.min_budget = 5000
        context.user_preferences.max_budget = 10000
        
        # Create filters with housing type
        filters = SearchFilters(
            search_type="property",
            housing_type="shared",
            city="Cairo",
        )
        
        # Apply preferences with root search message
        result = flow.apply_preferences_to_filters(context, filters, message="سكن مشترك")
        
        # Secondary filters should be reset
        assert result.tenant_type is None
        assert result.gender is None
        assert result.furnished is None
        assert result.min_price is None
        assert result.max_price is None
        
        # Location should be preserved
        assert result.city == "Cairo"
        assert result.housing_type == "shared"

    def test_apply_preferences_without_root_search(self):
        """Test that normal preference merge works without root search."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set up preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.min_budget = 5000
        
        # Create filters without housing type
        filters = SearchFilters(
            search_type="property",
            city="Cairo",
        )
        
        # Apply preferences without root search message
        result = flow.apply_preferences_to_filters(context, filters, message="للطلاب")
        
        # Preferences should be inherited normally
        assert result.tenant_type == "student"
        assert result.min_price == 5000

    def test_apply_preferences_with_housing_type_no_keyword(self):
        """Test that housing type without keyword doesn't trigger reset."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set up preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.min_budget = 5000
        
        # Create filters with housing type but message without keyword
        filters = SearchFilters(
            search_type="property",
            housing_type="shared",
            city="Cairo",
        )
        
        # Apply preferences with message that doesn't contain housing keyword
        result = flow.apply_preferences_to_filters(context, filters, message="للطلاب")
        
        # Preferences should be inherited normally (no reset)
        assert result.tenant_type == "student"
        assert result.min_price == 5000

    def test_preferences_cleared_after_reset(self):
        """Test that preferences are cleared after root search reset."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set up preferences
        context.user_preferences.tenant_type = "student"
        context.user_preferences.gender = "male"
        context.user_preferences.furnished = True
        context.user_preferences.min_budget = 5000
        context.user_preferences.max_budget = 10000
        
        # Create filters with housing type
        filters = SearchFilters(
            search_type="property",
            housing_type="shared",
            city="Cairo",
        )
        
        # Apply preferences with root search message
        flow.apply_preferences_to_filters(context, filters, message="سكن مشترك")
        
        # Preferences should be cleared
        assert context.user_preferences.tenant_type is None
        assert context.user_preferences.gender is None
        assert context.user_preferences.furnished is None
        assert context.user_preferences.min_budget is None
        assert context.user_preferences.max_budget is None

    def test_location_preserved_after_reset(self):
        """Test that location is preserved after reset."""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Set up location preference
        context.user_preferences.preferred_location = "Cairo"
        
        # Create filters with housing type
        filters = SearchFilters(
            search_type="property",
            housing_type="shared",
        )
        
        # Apply preferences with root search message
        result = flow.apply_preferences_to_filters(context, filters, message="سكن مشترك")
        
        # Location should be inherited
        assert result.governorate == "Cairo" or result.city == "Cairo"

    def test_case_1_shared_student_shared(self):
        """Test Case 1: سكن مشترك -> للطلاب -> سكن مشترك"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: سكن مشترك
        filters1 = SearchFilters(search_type="property", housing_type="shared")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="سكن مشترك")
        assert result1.tenant_type is None
        
        # Step 2: للطلاب (simulated by setting preference)
        context.user_preferences.tenant_type = "student"
        
        # Step 3: سكن مشترك again (should reset)
        filters3 = SearchFilters(search_type="property", housing_type="shared")
        result3 = flow.apply_preferences_to_filters(context, filters3, message="سكن مشترك")
        
        # Tenant type should be removed
        assert result3.tenant_type is None

    def test_case_2_apartment_furnished_price_apartment(self):
        """Test Case 2: شقة كاملة -> مفروشة -> فوق 5000 -> شقة كاملة"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: شقة كاملة
        filters1 = SearchFilters(search_type="property", housing_type="apartment")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="شقة كاملة")
        assert result1.furnished is None
        assert result1.min_price is None
        
        # Step 2: Add furnished and price (simulated by setting preferences)
        context.user_preferences.furnished = True
        context.user_preferences.min_budget = 5000
        
        # Step 3: شقة كاملة again (should reset)
        filters3 = SearchFilters(search_type="property", housing_type="apartment")
        result3 = flow.apply_preferences_to_filters(context, filters3, message="شقة كاملة")
        
        # Furnished and price should be removed
        assert result3.furnished is None
        assert result3.min_price is None

    def test_case_3_room_private_bathroom_room(self):
        """Test Case 3: غرفة -> حمام خاص -> غرفة"""
        flow = ConversationFlow()
        context = SessionContext()
        
        # Step 1: غرفة
        filters1 = SearchFilters(search_type="property", housing_type="room")
        result1 = flow.apply_preferences_to_filters(context, filters1, message="غرفة")
        assert result1.private_bathroom is None
        
        # Step 2: Add private bathroom (simulated by setting preference)
        context.user_preferences.private_bathroom = True
        
        # Step 3: غرفة again (should reset)
        filters3 = SearchFilters(search_type="property", housing_type="room")
        result3 = flow.apply_preferences_to_filters(context, filters3, message="غرفة")
        
        # Private bathroom should be removed
        assert result3.private_bathroom is None
