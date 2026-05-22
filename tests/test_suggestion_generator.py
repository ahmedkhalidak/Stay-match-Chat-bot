"""
Tests for Smart Dynamic Suggestions Generator.
"""

import pytest
from app.models.search_models import SearchFilters
from app.services.suggestion_generator import SuggestionGenerator


class TestSuggestionGenerator:
    """Test suite for SuggestionGenerator."""

    def test_apartment_search_suggestions(self):
        """Test apartment search returns correct suggestions."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "الأرخص" in labels
        assert "مفروشة" in labels
        assert "فيها واي فاي" in labels
        assert "المزيد" in labels

    def test_shared_housing_suggestions(self):
        """Test shared housing search returns correct suggestions."""
        filters = SearchFilters(search_type="shared")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "للطلاب" in labels
        assert "للبنات" in labels
        assert "الأرخص" in labels
        assert "المزيد" in labels

    def test_room_search_suggestions(self):
        """Test room search returns correct suggestions."""
        filters = SearchFilters(search_type="room")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "حمام خاص" in labels
        assert "مفروشة" in labels
        assert "غرفة خاصة" in labels
        assert "المزيد" in labels

    def test_large_result_set_narrowing_filters(self):
        """Test large result set (>20) returns narrowing filters."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=25,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "الأرخص" in labels
        assert "الأحدث" in labels
        assert "مفروشة" in labels
        assert "تحت 10000" in labels

    def test_small_result_set_expansion_buttons(self):
        """Test small result set (<=5) returns expansion buttons."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=3,
            has_more=False,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "أي مكان" in labels
        assert "بدون حد للسعر" in labels
        assert "شقة كاملة" in labels
        assert "سكن مشترك" in labels

    def test_no_results_recovery_suggestions(self):
        """Test no results returns recovery buttons."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_no_results_suggestions(filters)
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "أي مكان" in labels
        assert "بدون حد للسعر" in labels
        assert "شقة كاملة" in labels
        assert "سكن مشترك" in labels

    def test_clarification_suggestions(self):
        """Test clarification suggestions for ambiguous intent."""
        suggestions = SuggestionGenerator.generate_clarification_suggestions()
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "🏠 شقة كاملة" in labels
        assert "👥 سكن مشترك" in labels
        assert "🚪 غرفة" in labels

    def test_slot_suggestions_search_type(self):
        """Test slot suggestions for search_type."""
        suggestions = SuggestionGenerator.get_slot_suggestions("search_type")
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "أوضة" in labels
        assert "شقة كاملة" in labels
        assert "شقة مشتركة" in labels

    def test_slot_suggestions_location(self):
        """Test slot suggestions for location."""
        suggestions = SuggestionGenerator.get_slot_suggestions("location")
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "المعادي" in labels
        assert "الإسكندرية" in labels
        assert "أي مكان" in labels

    def test_slot_suggestions_price(self):
        """Test slot suggestions for price."""
        suggestions = SuggestionGenerator.get_slot_suggestions("price")
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "تحت 3000" in labels
        assert "تحت 5000" in labels
        assert "تحت 10000" in labels
        assert "أي سعر" in labels

    def test_slot_suggestions_housing_type(self):
        """Test slot suggestions for housing_type."""
        suggestions = SuggestionGenerator.get_slot_suggestions("housing_type")
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "🏠 شقة كاملة" in labels
        assert "🚪 غرفة" in labels
        assert "👥 سكن مشترك" in labels
        assert "اعرض الكل" in labels

    def test_followup_apartment_suggestions(self):
        """Test follow-up suggestions after apartment search."""
        filters = SearchFilters(search_type="full")
        suggestions = SuggestionGenerator.generate_followup_suggestions(
            filters=filters,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "الأرخص" in labels
        assert "الأحدث" in labels
        assert "مفروشة" in labels
        assert "المزيد" in labels

    def test_followup_shared_suggestions(self):
        """Test follow-up suggestions after shared housing search."""
        filters = SearchFilters(search_type="shared")
        suggestions = SuggestionGenerator.generate_followup_suggestions(
            filters=filters,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "للطلاب" in labels
        assert "للبنات" in labels
        assert "الأرخص" in labels
        assert "المزيد" in labels

    def test_followup_room_suggestions(self):
        """Test follow-up suggestions after room search."""
        filters = SearchFilters(search_type="room")
        suggestions = SuggestionGenerator.generate_followup_suggestions(
            filters=filters,
            has_more=True,
        )
        
        assert len(suggestions) <= 4
        labels = [s.label for s in suggestions]
        assert "حمام خاص" in labels
        assert "مفروشة" in labels
        assert "غرفة خاصة" in labels
        assert "المزيد" in labels

    def test_max_four_suggestions_enforced(self):
        """Test that all methods return at most 4 suggestions."""
        filters = SearchFilters(search_type="property")
        
        # Test all methods
        result_suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        no_results_suggestions = SuggestionGenerator.generate_no_results_suggestions(filters)
        clarification_suggestions = SuggestionGenerator.generate_clarification_suggestions()
        followup_suggestions = SuggestionGenerator.generate_followup_suggestions(
            filters=filters,
            has_more=True,
        )
        slot_suggestions = SuggestionGenerator.get_slot_suggestions("search_type")
        
        assert len(result_suggestions) <= 4
        assert len(no_results_suggestions) <= 4
        assert len(clarification_suggestions) <= 4
        assert len(followup_suggestions) <= 4
        assert len(slot_suggestions) <= 4

    def test_suggestion_structure(self):
        """Test that all suggestions have correct structure (label and value)."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        
        for suggestion in suggestions:
            assert hasattr(suggestion, "label")
            assert hasattr(suggestion, "value")
            assert isinstance(suggestion.label, str)
            assert isinstance(suggestion.value, str)
            assert len(suggestion.label) > 0
            assert len(suggestion.value) > 0

    def test_edge_case_exactly_20_results(self):
        """Test edge case with exactly 20 results (should not trigger large result logic)."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=20,
            has_more=True,
        )
        
        # Should use apartment-specific suggestions, not large result narrowing
        labels = [s.label for s in suggestions]
        assert "الأحدث" not in labels  # This is only in large result suggestions
        assert "تحت 10000" not in labels  # This is only in large result suggestions

    def test_edge_case_exactly_5_results(self):
        """Test edge case with exactly 5 results (should trigger small result logic per RULE 3)."""
        filters = SearchFilters(search_type="property")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=5,
            has_more=True,
        )
        
        # Should use small result expansion (RULE 3: total_results <= 5)
        labels = [s.label for s in suggestions]
        assert "أي مكان" in labels  # This is in small result suggestions
        assert "بدون حد للسعر" in labels  # This is in small result suggestions
        assert "شقة كاملة" in labels  # This is in small result suggestions
        assert "سكن مشترك" in labels  # This is in small result suggestions

    def test_unknown_search_type_fallback(self):
        """Test fallback for unknown search type."""
        filters = SearchFilters(search_type="unknown")
        suggestions = SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=10,
            has_more=True,
        )
        
        # Should return default fallback suggestions
        assert len(suggestions) <= 4
        assert len(suggestions) > 0
