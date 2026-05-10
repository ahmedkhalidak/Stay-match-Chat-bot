from app.models.search_models import (
    SearchFilters,
)

from app.ranking.services.location_service import (
    LocationService,
)


class FilterValidator:

    VALID_SORTS = {
        "price_low",
        "price_high",
        "relevance",
    }

    VALID_SEARCH_TYPES = {
        "room",
        "property",
    }

    VALID_TENANT_TYPES = {
        "student",
        "worker",
    }

    def __init__(self):

        self.location_service = (
            LocationService()
        )

    def validate(
        self,
        filters: SearchFilters,
    ) -> SearchFilters:

        self._validate_search_type(
            filters
        )

        self._validate_sort(
            filters
        )

        self._validate_tenant_type(
            filters
        )

        self._validate_prices(
            filters
        )

        self._validate_location(
            filters
        )

        return filters

    # ──────────────────────────────────────────
    # Search Type
    # ──────────────────────────────────────────

    def _validate_search_type(
        self,
        filters: SearchFilters,
    ):

        if (
            filters.search_type
            not in self.VALID_SEARCH_TYPES
        ):

            filters.search_type = None

    # ──────────────────────────────────────────
    # Sort
    # ──────────────────────────────────────────

    def _validate_sort(
        self,
        filters: SearchFilters,
    ):

        if (
            filters.sort_by
            not in self.VALID_SORTS
        ):

            filters.sort_by = "relevance"

    # ──────────────────────────────────────────
    # Tenant Type
    # ──────────────────────────────────────────

    def _validate_tenant_type(
        self,
        filters: SearchFilters,
    ):

        if (
            filters.tenant_type
            not in self.VALID_TENANT_TYPES
        ):

            filters.tenant_type = None

    # ──────────────────────────────────────────
    # Prices
    # ──────────────────────────────────────────

    def _validate_prices(
        self,
        filters: SearchFilters,
    ):

        if (
            filters.min_price
            is not None
            and filters.min_price < 0
        ):

            filters.min_price = None

        if (
            filters.max_price
            is not None
            and filters.max_price < 0
        ):

            filters.max_price = None

        # swap wrong ranges
        if (
            filters.min_price
            is not None
            and filters.max_price
            is not None
            and filters.min_price
            > filters.max_price
        ):

            (
                filters.min_price,
                filters.max_price,
            ) = (
                filters.max_price,
                filters.min_price,
            )

    # ──────────────────────────────────────────
    # Location
    # ──────────────────────────────────────────

    def _validate_location(
        self,
        filters: SearchFilters,
    ):

        if not filters.city:
            return

        detected = (
            self.location_service.detect_location(
                filters.city
            )
        )

        if not detected:

            filters.city = None
            filters.governorate = None

            return

        filters.city = detected[
            "city"
        ]

        filters.governorate = detected[
            "governorate"
        ]