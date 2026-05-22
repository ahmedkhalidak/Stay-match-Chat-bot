import unittest

from app.models.search_models import SearchFilters
from app.nlp.nlp_pipeline import NLPPipeline
from app.utils.text_normalizer import TextNormalizer


class NLPPipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = NLPPipeline()
        self.last_search = SearchFilters(
            intent="room_search",
            search_type="room",
            city="Maadi",
            max_price=4000,
        )

    def assert_filters(self, message, expected, **kwargs):
        filters = self.pipeline.extract(message, **kwargs)
        for field, value in expected.items():
            with self.subTest(message=message, field=field):
                self.assertEqual(getattr(filters, field), value)

    def test_pdf_regression_matrix(self):
        cases = [
            ("عايز اوضة في المعادي", {"search_type": "room", "city": "Maadi"}),
            ("عايز اوضة في االسماعيلية", {"search_type": "room", "governorate": "Ismailia"}),
            ("عايز اوضة في القاهرة", {"search_type": "room", "governorate": "Cairo"}),
            ("عايز اوضة تحت 4000", {"search_type": "room", "max_price": 4000}),
            ("عايز اوضة فوق 5000", {"search_type": "room", "min_price": 5000}),
            ("عايز اوضة بين 3000 و 5000", {"search_type": "room", "min_price": 3000, "max_price": 5000}),
            ("عايز ارخص اوضة", {"search_type": "room", "sort_by": "price_low"}),
            ("عايز اغلى اوضة", {"search_type": "room", "sort_by": "price_high"}),
            ("عايز اوضة فيها واي فاي", {"search_type": "room", "wifi": True}),
            ("عايز اوضة مفروشة", {"search_type": "room", "furnished": True}),
            ("عايز اوضة فيها حمام خاص", {"search_type": "room", "private_bathroom": True}),
            ("عايز اوضة فيها بلكونة", {"search_type": "room", "balcony": True}),
            ("عايز اوضة مشتركة", {"search_type": "room", "shared_room": True}),
            ("عايز شقة في االسماعيلية", {"search_type": "property", "governorate": "Ismailia"}),
            ("عايز شقة مفروشة", {"search_type": "property", "furnished": True}),
            ("عايز شقة تحت 10000", {"search_type": "property", "max_price": 10000}),
            ("عايز شقة فيها واي فاي", {"search_type": "property", "wifi": True}),
            ("عايز اوضة في اسماعلية", {"search_type": "room", "governorate": "Ismailia"}),
            ("عايز اوضة في االسمعيلية", {"search_type": "room", "governorate": "Ismailia"}),
            ("عايز شقة في معادي", {"search_type": "property", "city": "Maadi"}),
            ("عايز اوضة ف االسمعليه", {"search_type": "room", "governorate": "Ismailia"}),
            ("عايز ارخص اوضة في المعادي", {"search_type": "room", "city": "Maadi", "sort_by": "price_low"}),
            ("عايز اغلى اوضة في المعادي", {"search_type": "room", "city": "Maadi", "sort_by": "price_high"}),
            ("رتبلي من الارخص للاعلى", {"sort_by": "price_low"}),
            ("هات الاعلى سعرا", {"sort_by": "price_high"}),
        ]

        for message, expected in cases:
            self.assert_filters(message, expected)

    def test_follow_up_regression_matrix(self):
        cases = [
            ("للطلاب", {"intent": "follow_up", "search_type": "room", "city": "Maadi", "tenant_type": "student"}),
            ("فيها واي فاي", {"search_type": "room", "city": "Maadi", "wifi": True}),
            ("مش عايز واي فاي", {"search_type": "room", "city": "Maadi", "wifi": False}),
            ("مش عايز تكييف", {"search_type": "room", "city": "Maadi", "air_conditioning": False}),
            ("غير مفروشة", {"search_type": "room", "city": "Maadi", "furnished": False}),
            ("في اسكندرية بدل المعادي", {"search_type": "room", "governorate": "Alexandria", "max_price": 4000}),
        ]

        for message, expected in cases:
            self.assert_filters(message, expected, last_search=self.last_search)

    def test_room_request_does_not_create_fake_location(self):
        filters = self.pipeline.extract("عايز اوضة")
        self.assertEqual(filters.search_type, "room")
        self.assertIsNone(filters.city)
        self.assertIsNone(filters.governorate)

    def test_shared_apartment_and_shared_room_are_distinct(self):
        shared_property = self.pipeline.extract("شقة مشتركة في القاهرة")
        shared_room = self.pipeline.extract("عايز اوضة مشتركة")
        self.assertEqual(shared_property.search_type, "shared")
        self.assertEqual(shared_room.search_type, "room")
        self.assertTrue(shared_room.shared_room)

    def test_private_bathroom_does_not_force_private_room(self):
        filters = self.pipeline.extract("عايز اوضة فيها حمام خاص")
        self.assertTrue(filters.private_bathroom)
        self.assertIsNone(filters.shared_room)

    def test_explicit_housing_noun_keeps_search_intent(self):
        room = self.pipeline.extract("عايز اوضة فيها واي فاي")
        prop = self.pipeline.extract("عايز شقة مفروشة")
        self.assertEqual(room.intent, "room_search")
        self.assertEqual(prop.intent, "property_search")

    def test_numeric_normalization_preserves_prices_and_real_double_letters(self):
        self.assertIn("4000", TextNormalizer.normalize("تحت 4000"))
        self.assertIn("تكييف", TextNormalizer.normalize("مش عايز تكييف"))

    def test_any_price_does_not_create_fake_wifi_filter(self):
        filters = self.pipeline.extract("أي سعر")
        self.assertIsNone(filters.wifi)

    def test_housing_type_priority_rules(self):
        """
        Test that shared keywords override apartment keywords.
        This ensures "شقة مشتركة" is classified as shared, not apartment.
        """
        cases = [
            # Full apartment cases
            ("شقة كاملة", {"housing_type": "apartment", "search_type": "full"}),
            ("شقه كامله", {"housing_type": "apartment", "search_type": "full"}),
            ("apartment", {"housing_type": "apartment", "search_type": "full"}),
            ("flat", {"housing_type": "apartment", "search_type": "full"}),

            # Shared housing cases (must override apartment keywords)
            ("شقة مشتركة", {"housing_type": "shared", "search_type": "shared"}),
            ("شقه مشتركه", {"housing_type": "shared", "search_type": "shared"}),
            ("سكن مشترك", {"housing_type": "shared", "search_type": "shared"}),
            ("shared apartment", {"housing_type": "shared", "search_type": "shared"}),
            ("shared flat", {"housing_type": "shared", "search_type": "shared"}),
            ("غرفة مشتركة", {"housing_type": "shared", "search_type": "shared"}),

            # Room cases
            ("غرفة", {"housing_type": "room", "search_type": "room"}),
            ("غرفه", {"housing_type": "room", "search_type": "room"}),
            ("غرف", {"housing_type": "room", "search_type": "room"}),
            ("اوضة", {"housing_type": "room", "search_type": "room"}),
            ("اوضه", {"housing_type": "room", "search_type": "room"}),
            ("room", {"housing_type": "room", "search_type": "room"}),
            ("rooms", {"housing_type": "room", "search_type": "room"}),
            ("bedroom", {"housing_type": "room", "search_type": "room"}),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                filters = self.pipeline.extract(message)
                for field, value in expected.items():
                    self.assertEqual(getattr(filters, field), value,
                                   f"Failed for message '{message}': expected {field}={value}, got {getattr(filters, field)}")

    def test_price_filter_extraction(self):
        """Test price filter extraction for different patterns"""
        cases = [
            ("اقل من 5000", {"min_price": None, "max_price": 5000}),
            ("ازيد من 5000", {"min_price": 5000, "max_price": None}),
            ("بين 3000 و 7000", {"min_price": 3000, "max_price": 7000}),
            ("تحت 4000", {"min_price": None, "max_price": 4000}),
            ("فوق 6000", {"min_price": 6000, "max_price": None}),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                filters = self.pipeline.extract(message)
                self.assertEqual(filters.min_price, expected["min_price"],
                               f"Failed for message '{message}': expected min_price={expected['min_price']}, got {filters.min_price}")
                self.assertEqual(filters.max_price, expected["max_price"],
                               f"Failed for message '{message}': expected max_price={expected['max_price']}, got {filters.max_price}")

    def test_price_filter_override_sequence(self):
        """Test that explicit price overrides clear conflicting previous price filters"""
        # First message: "اقل من 5000"
        filters1 = self.pipeline.extract("اقل من 5000")
        self.assertEqual(filters1.min_price, None)
        self.assertEqual(filters1.max_price, 5000)

        # Simulate context with previous search
        last_search = SearchFilters(
            min_price=None,
            max_price=5000,
            city="Cairo",
        )

        # Second message: "ازيد من 5000" should override previous max_price
        filters2 = self.pipeline.extract("ازيد من 5000", last_search=last_search)
        self.assertEqual(filters2.min_price, 5000,
                        f"Expected min_price=5000, got {filters2.min_price}")
        self.assertEqual(filters2.max_price, None,
                        f"Expected max_price=None (cleared), got {filters2.max_price}")

    def test_price_filter_with_location_preserved(self):
        """Test that location is preserved when price changes"""
        last_search = SearchFilters(
            min_price=None,
            max_price=5000,
            city="Maadi",
        )

        filters = self.pipeline.extract("ازيد من 4000", last_search=last_search)
        self.assertEqual(filters.min_price, 4000)
        self.assertEqual(filters.max_price, None)
        self.assertEqual(filters.city, "Maadi", "Location should be preserved")

    def test_room_detection_with_context_switch(self):
        """
        Test that room keywords override previous apartment context.
        This ensures "غرف" after "شقة" switches to room search.
        """
        # First message: apartment
        filters1 = self.pipeline.extract("شقة")
        self.assertEqual(filters1.housing_type, "apartment")
        self.assertEqual(filters1.search_type, "full")

        # Second message: room (should override previous apartment)
        last_search = SearchFilters(
            housing_type="apartment",
            search_type="full",
            city="Cairo",
        )
        filters2 = self.pipeline.extract("غرف", last_search=last_search)
        self.assertEqual(filters2.housing_type, "room",
                        f"Expected housing_type=room, got {filters2.housing_type}")
        self.assertEqual(filters2.search_type, "room",
                        f"Expected search_type=room, got {filters2.search_type}")

    def test_room_detection_with_location(self):
        """
        Test that room detection works with location.
        """
        cases = [
            ("غرفة في القاهرة", {"housing_type": "room", "search_type": "room", "governorate": "Cairo"}),
            ("غرف في المعادي", {"housing_type": "room", "search_type": "room", "city": "Maadi"}),
            ("rooms in Cairo", {"housing_type": "room", "search_type": "room", "governorate": "Cairo"}),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                filters = self.pipeline.extract(message)
                for field, value in expected.items():
                    self.assertEqual(getattr(filters, field), value,
                                   f"Failed for message '{message}': expected {field}={value}, got {getattr(filters, field)}")


if __name__ == "__main__":
    unittest.main()
