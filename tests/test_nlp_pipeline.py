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


if __name__ == "__main__":
    unittest.main()
