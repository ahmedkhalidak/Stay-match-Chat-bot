import asyncio
import unittest

from app.core.memory_store import memory_store
from app.services.search_service import SearchService


def make_room(room_id: int, city: str = "Maadi"):
    return {
        "Id": room_id,
        "RoomName": f"Room {room_id}",
        "PropertyName": "Test Property",
        "City": city,
        "Government": "Cairo",
        "Street": "Street 1",
        "Month_rent": 4000 + room_id,
        "Deposit": 1000,
        "Capacity": 1,
        "CapacityAvailable": 1,
        "Furnished": True,
        "Wifi": True,
        "AirConditioning": True,
        "Balcony": False,
        "EnSuiteBathroom": False,
        "MinimumStay": 3,
    }


def make_property(property_id: int):
    return {
        "Id": property_id,
        "Name": f"Property {property_id}",
        "MonthlyRent": 9000,
        "Deposite": 2000,
        "City": "Maadi",
        "Government": "Cairo",
        "TotalRooms": 3,
        "AvailableRooms": 2,
        "Furnished": True,
        "Size": 120,
        "MinimumStay": 6,
        "TotalRoomsCount": 3,
        "RoomMinPrice": 3000,
        "RoomMaxPrice": 4500,
        "Wifi": True,
        "AirConditioning": True,
        "FreeParking": False,
    }


class FakeRoomRepository:
    def __init__(self):
        self.rows = [make_room(room_id) for room_id in range(1, 7)]
        self.calls = []

    def search(self, filters, offset=0, limit=5):
        self.calls.append(filters.model_copy(deep=True))
        if filters.city == "Alexandria" or filters.governorate == "Alexandria":
            return []
        return self.rows[offset:offset + limit]

    def count(self, filters):
        if filters.city == "Alexandria" or filters.governorate == "Alexandria":
            return 0
        return len(self.rows)


class FakePropertyRepository:
    def __init__(self):
        self.rows = [make_property(1)]
        self.calls = []

    def search(self, filters, offset=0, limit=5):
        self.calls.append(filters.model_copy(deep=True))
        return self.rows[offset:offset + limit]

    def count(self, filters):
        return len(self.rows)


def _run(coro):
    return asyncio.run(coro)


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = SearchService()
        self.service.room_repo = FakeRoomRepository()
        self.service.property_repo = FakePropertyRepository()
        self.sessions = [
            "flow", "paging", "skip", "no-results", "property",
            "history", "small-talk", "faq", "invalid", "room-gov",
            "room-city", "switch-1", "budget-1", "amenities-1",
            "lang-switch", "flutter-apartment", "flutter-room",
            "flutter-add", "flutter-booking", "flutter-ratings", "flutter-support",
            "flutter-flow",
        ]
        for sid in self.sessions:
            memory_store.get_context_sync(sid)
            memory_store._store.pop(sid, None)

    def test_short_slot_filling_flow_returns_structured_results(self):
        first = _run(self.service.handle_message("flow", "عايز اوضة"))
        self.assertEqual(first.response_type, "clarification")
        self.assertEqual(first.pending_slot, "location")

        second = _run(self.service.handle_message("flow", "في المعادي"))
        self.assertEqual(second.response_type, "clarification")
        self.assertEqual(second.pending_slot, "price")

        third = _run(self.service.handle_message("flow", "أي سعر"))
        self.assertEqual(third.response_type, "results")
        self.assertEqual(len(third.results), 5)
        self.assertEqual(third.results[0].result_type, "room")
        self.assertTrue(third.pagination.has_more)
        self.assertTrue(third.suggestions)

    def test_show_more_fetches_next_page(self):
        first = _run(self.service.handle_message("paging", "عايز اوضة في المعادي تحت 5000"))
        self.assertEqual(first.response_type, "results")
        self.assertEqual(len(first.results), 5)
        self.assertTrue(first.pagination.has_more)

        second = _run(self.service.handle_message("paging", "المزيد"))
        self.assertEqual(second.response_type, "results")
        self.assertEqual(len(second.results), 1)
        self.assertFalse(second.pagination.has_more)

    def test_any_location_and_any_price_skip_optional_slots(self):
        first = _run(self.service.handle_message("skip", "أوضة"))
        second = _run(self.service.handle_message("skip", "أي مكان"))
        third = _run(self.service.handle_message("skip", "أي سعر"))

        self.assertEqual(first.pending_slot, "location")
        self.assertEqual(second.pending_slot, "price")
        self.assertEqual(third.response_type, "results")
        self.assertIsNone(third.filters.city)
        self.assertIsNone(third.filters.max_price)

    def test_no_results_returns_clean_frontend_payload(self):
        _run(self.service.handle_message("no-results", "أوضة"))
        _run(self.service.handle_message("no-results", "في الإسكندرية"))
        response = _run(self.service.handle_message("no-results", "أي سعر"))

        self.assertEqual(response.response_type, "no_results")
        self.assertEqual(response.results, [])
        self.assertFalse(response.pagination.has_more)
        self.assertTrue(response.suggestions)

    def test_property_search_uses_property_cards(self):
        response = _run(self.service.handle_message("property", "عايز شقة كاملة في المعادي تحت 10000"))
        self.assertEqual(response.response_type, "results")
        self.assertEqual(response.results[0].result_type, "property")
        self.assertEqual(response.filters.search_type, "full")

    def test_go_back_returns_previous_search(self):
        _run(self.service.handle_message("history", "عايز اوضة في المعادي تحت 5000"))
        second = _run(self.service.handle_message("history", "فيها واي فاي"))
        back = _run(self.service.handle_message("history", "ارجع"))

        self.assertTrue(second.filters.wifi)
        self.assertEqual(back.response_type, "results")
        self.assertIsNone(back.filters.wifi)

    def test_small_talk_faq_and_invalid_are_typed(self):
        small_talk = _run(self.service.handle_message("small-talk", "هاي"))
        faq = _run(self.service.handle_message("faq", "ايه هو staymatch"))
        invalid = _run(self.service.handle_message("invalid", "احجزلي طيارة"))

        self.assertEqual(small_talk.response_type, "small_talk")
        self.assertEqual(faq.response_type, "faq")
        self.assertEqual(invalid.response_type, "fallback")
        self.assertTrue(invalid.suggestions)

    def test_room_search_by_governorate(self):
        response = _run(self.service.handle_message("room-gov", "غرف في القاهرة"))
        self.assertEqual(response.response_type, "results")
        self.assertEqual(response.filters.search_type, "room")
        self.assertEqual(response.filters.housing_type, "room")

    def test_room_search_by_city(self):
        response = _run(self.service.handle_message("room-city", "غرف في المعادي"))
        self.assertEqual(response.response_type, "results")
        self.assertEqual(response.filters.search_type, "room")
        self.assertEqual(response.filters.housing_type, "room")
        self.assertEqual(response.filters.city, "Maadi")

    def test_housing_type_switch_resets_pagination(self):
        first = _run(self.service.handle_message("switch-1", "شقق في القاهرة مفروشة"))
        self.assertEqual(first.response_type, "results")
        self.assertEqual(first.filters.housing_type, "apartment")
        self.assertTrue(first.filters.furnished)

        second = _run(self.service.handle_message("switch-1", "غرف"))
        self.assertEqual(second.response_type, "results")
        self.assertEqual(second.filters.housing_type, "room")
        self.assertIsNone(second.filters.furnished, "Optional filters should be cleared")
        self.assertEqual(second.filters.governorate, "Cairo", "Location should be preserved")

    def test_housing_type_switch_preserves_budget(self):
        first = _run(self.service.handle_message("budget-1", "شقق تحت 10000"))
        self.assertEqual(first.response_type, "results")
        self.assertEqual(first.filters.housing_type, "apartment")
        self.assertEqual(first.filters.max_price, 10000)

        second = _run(self.service.handle_message("budget-1", "غرف"))
        self.assertEqual(second.response_type, "results")
        self.assertEqual(second.filters.housing_type, "room")
        self.assertEqual(second.filters.max_price, 10000, "Budget should be preserved")

    def test_housing_type_switch_clears_amenities(self):
        first = _run(self.service.handle_message("amenities-1", "شقق مشتركة فيها واي فاي"))
        self.assertEqual(first.response_type, "results")
        self.assertEqual(first.filters.housing_type, "shared")
        self.assertTrue(first.filters.wifi)

        second = _run(self.service.handle_message("amenities-1", "غرف"))
        self.assertEqual(second.response_type, "results")
        self.assertEqual(second.filters.housing_type, "room")
        self.assertIsNone(second.filters.wifi, "Amenity filters should be cleared")

    def test_english_conversation_flow(self):
        """Test that English messages are handled correctly."""
        first = _run(self.service.handle_message("en-flow", "I want a room"))
        self.assertEqual(first.response_type, "clarification")
        self.assertEqual(first.pending_slot, "location")
        self.assertEqual(first.filters.search_type, "room")

        second = _run(self.service.handle_message("en-flow", "in Maadi"))
        self.assertEqual(second.response_type, "clarification")
        self.assertEqual(second.pending_slot, "price")

        third = _run(self.service.handle_message("en-flow", "any price"))
        self.assertEqual(third.response_type, "results")
        self.assertEqual(len(third.results), 5)
        self.assertEqual(third.results[0].result_type, "room")

    def test_language_switches_per_incoming_message(self):
        first = _run(self.service.handle_message("lang-switch", "عايز اوضة"))
        self.assertIn("تحب تدور فين", first.reply)

        second = _run(self.service.handle_message("lang-switch", "in Maadi"))
        self.assertIn("monthly budget", second.reply)

        third = _run(self.service.handle_message("lang-switch", "أي سعر"))
        self.assertTrue(third.reply.startswith("لقيت"))

        fourth = _run(self.service.handle_message("lang-switch", "more"))
        self.assertTrue(fourth.reply.startswith("Found"))

    def test_flutter_sidebar_search_shortcuts(self):
        apartment = _run(self.service.handle_message("flutter-apartment", "find_full_apartment"))
        self.assertEqual(apartment.response_type, "find_apartment")
        self.assertEqual(apartment.pending_slot, "location")
        self.assertEqual(apartment.filters.search_type, "full")
        self.assertEqual(apartment.filters.housing_type, "apartment")
        self.assertEqual(len(apartment.suggestions), 4)

        room = _run(self.service.handle_message("flutter-room", "find_room"))
        self.assertEqual(room.response_type, "find_room")
        self.assertEqual(room.pending_slot, "location")
        self.assertEqual(room.filters.search_type, "room")
        self.assertEqual(room.filters.housing_type, "room")

    def test_flutter_sidebar_help_shortcuts(self):
        cases = [
            ("flutter-add", "how_to_add_property", "add_property_help"),
            ("flutter-booking", "booking_help", "booking_help"),
            ("flutter-ratings", "ratings_help", "ratings_help"),
            ("flutter-support", "support_help", "support_help"),
        ]
        for session_id, message, response_type in cases:
            with self.subTest(message=message):
                response = _run(self.service.handle_message(session_id, message))
                self.assertEqual(response.response_type, response_type)
                self.assertTrue(response.reply)
                self.assertTrue(response.suggestions)

    def test_flutter_demo_search_flow(self):
        first = _run(self.service.handle_message("flutter-flow", "عاوز شقة"))
        self.assertEqual(first.response_type, "clarification")
        self.assertEqual(first.pending_slot, "location")
        self.assertEqual(
            [suggestion.label for suggestion in first.suggestions],
            ["القاهرة", "المعادي", "الإسكندرية", "أي مكان"],
        )

        second = _run(self.service.handle_message("flutter-flow", "cairo"))
        self.assertEqual(second.response_type, "clarification")
        self.assertEqual(second.pending_slot, "price")

        third = _run(self.service.handle_message("flutter-flow", "أي سعر"))
        self.assertEqual(third.response_type, "results")
        self.assertTrue(third.results)
        self.assertIn("مفروشة", [suggestion.label for suggestion in third.suggestions])

        fourth = _run(self.service.handle_message("flutter-flow", "مفروشة"))
        self.assertEqual(fourth.response_type, "results")
        self.assertTrue(fourth.filters.furnished)


if __name__ == "__main__":
    unittest.main()
