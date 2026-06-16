from app.models.response_models import SearchResultItem


class ResponseFormatter:
    """
    Converts DB rows into concise chat copy plus frontend-friendly result cards.
    """

    def format_rooms(
        self,
        rooms,
        filters=None,
        has_more: bool = False,
        page_num: int = 1,
        scores: dict[int, float] = None,
        lang: str = "ar",
    ) -> tuple[str, list[SearchResultItem]]:
        cards = [self._room_card(room, scores, lang=lang) for room in rooms]
        location = self._filter_location(filters)
        header = self._result_header(
            count=len(cards),
            label="room" if lang == "en" else "أوضة",
            location=location,
            page_num=page_num,
            has_more=has_more,
            lang=lang,
        )
        return header, cards

    def format_properties(
        self,
        properties,
        filters=None,
        has_more: bool = False,
        page_num: int = 1,
        scores: dict[int, float] = None,
        lang: str = "ar",
    ) -> tuple[str, list[SearchResultItem]]:
        cards = [self._property_card(prop, filters, scores, lang=lang) for prop in properties]
        search_type = filters.search_type if filters else "property"
        labels = {
            "en": {
                "shared": "shared housing option",
                "full": "apartment",
                "property": "property",
            },
            "ar": {
                "shared": "شقة مشتركة",
                "full": "شقة كاملة",
                "property": "شقة",
            },
        }
        language_labels = labels.get(lang, labels["ar"])
        label = language_labels.get(search_type, language_labels["property"])
        location = self._filter_location(filters)
        header = self._result_header(
            count=len(cards),
            label=label,
            location=location,
            page_num=page_num,
            has_more=has_more,
            lang=lang,
        )
        return header, cards

    def _result_header(
        self,
        count: int,
        label: str,
        location: str | None,
        page_num: int,
        has_more: bool,
        lang: str = "ar",
    ) -> str:
        if lang == "en":
            page_text = f" - page {page_num}" if page_num > 1 else ""
            location_text = f" in {location}" if location else ""
            plural = "" if count == 1 else "s"
            more_text = " There are more results available." if has_more else ""
            return f"Found {count} {label}{plural}{location_text}{page_text}.{more_text}".strip()

        page_text = f" - صفحة {page_num}" if page_num > 1 else ""
        location_text = f" في {location}" if location else ""
        more_text = " فيه نتائج تانية كمان." if has_more else ""
        return f"لقيت {count} {label}{location_text}{page_text}.{more_text}".strip()

    def _room_card(self, room, scores=None, lang: str = "ar") -> SearchResultItem:
        location = self._row_location(
            city=room.get("City"),
            governorate=room.get("Government"),
            street=room.get("Street"),
            lang=lang,
        )
        monthly_rent = self._as_int(room.get("Month_rent"))
        deposit = self._as_int(room.get("Deposit"))

        details = []
        capacity = room.get("Capacity") or 1
        capacity_available = room.get("CapacityAvailable")
        if capacity > 1:
            details.append(
                f"Shared {capacity_available or 0}/{capacity}"
                if lang == "en"
                else f"مشتركة {capacity_available or 0}/{capacity}"
            )
        else:
            details.append("Single" if lang == "en" else "سنجل")

        minimum_stay = room.get("MinimumStay")
        if minimum_stay:
            details.append(
                f"Minimum stay {minimum_stay} month(s)"
                if lang == "en"
                else f"حد أدنى {minimum_stay} شهر"
            )

        amenities = self._amenities_from_row(room, room_scope=True, lang=lang)

        return SearchResultItem(
            id=room.get("Id", "?"),
            result_type="room",
            title=room.get("RoomName") or ("Room" if lang == "en" else "أوضة"),
            subtitle=room.get("PropertyName") or ("Property" if lang == "en" else "عقار"),
            location=location,
            price_text=self._price_text(
                monthly_rent,
                unit="month" if lang == "en" else "شهر",
                lang=lang,
            ),
            monthly_rent=monthly_rent,
            deposit=deposit,
            details=details,
            amenities=amenities,
            attributes={
                "capacity": capacity,
                "capacity_available": capacity_available,
                "furnished": bool(room.get("Furnished")),
                "shared_room": capacity > 1,
            },
            recommendation_score=scores.get(room.get("Id")) if scores else None,
        )

    def _property_card(self, prop, filters, scores=None, lang: str = "ar") -> SearchResultItem:
        search_type = filters.search_type if filters else "property"
        location = self._row_location(
            city=prop.get("City"),
            governorate=prop.get("Government"),
            lang=lang,
        )
        monthly_rent = self._as_int(prop.get("MonthlyRent"))
        deposit = self._as_int(prop.get("Deposite"))
        room_min = self._as_int(prop.get("RoomMinPrice"))
        room_max = self._as_int(prop.get("RoomMaxPrice"))

        details = []
        if search_type == "shared":
            room_count = prop.get("TotalRoomsCount") or 0
            if room_count:
                details.append(f"{room_count} rooms" if lang == "en" else f"{room_count} أوض")
        else:
            total_rooms = prop.get("TotalRooms")
            if total_rooms:
                details.append(f"{total_rooms} rooms" if lang == "en" else f"{total_rooms} غرف")

        available_rooms = prop.get("AvailableRooms")
        if available_rooms is not None:
            details.append(f"{available_rooms} available" if lang == "en" else f"{available_rooms} متاحة")

        size = self._as_int(prop.get("Size"))
        if size:
            details.append(f"{size} m2" if lang == "en" else f"{size} م2")

        minimum_stay = prop.get("MinimumStay")
        if minimum_stay:
            details.append(f"Minimum stay {minimum_stay} month(s)" if lang == "en" else f"حد أدنى {minimum_stay} شهر")

        return SearchResultItem(
            id=prop.get("Id", "?"),
            result_type="property",
            title=prop.get("Name") or ("Apartment" if lang == "en" else "شقة"),
            location=location,
            price_text=self._property_price_text(
                search_type=search_type,
                monthly_rent=monthly_rent,
                room_min=room_min,
                room_max=room_max,
                lang=lang,
            ),
            monthly_rent=monthly_rent,
            deposit=deposit,
            details=details,
            amenities=self._amenities_from_row(prop, room_scope=False, lang=lang),
            attributes={
                "search_type": search_type,
                "furnished": bool(prop.get("Furnished")),
                "room_min_price": room_min,
                "room_max_price": room_max,
            },
        )

    def _amenities_from_row(self, row, room_scope: bool, lang: str = "ar") -> list[str]:
        amenities = []
        if row.get("Furnished"):
            amenities.append("Furnished" if lang == "en" else "مفروشة")
        if row.get("Wifi"):
            amenities.append("WiFi" if lang == "en" else "واي فاي")
        if row.get("AirConditioning"):
            amenities.append("Air conditioning" if lang == "en" else "تكييف")
        if row.get("Balcony"):
            amenities.append("Balcony" if lang == "en" else "بلكونة")
        if room_scope and row.get("EnSuiteBathroom"):
            amenities.append("Private bathroom" if lang == "en" else "حمام خاص")
        if row.get("FreeParking"):
            amenities.append("Parking" if lang == "en" else "موقف")
        return amenities

    def _property_price_text(
        self,
        search_type: str,
        monthly_rent: int | None,
        room_min: int | None,
        room_max: int | None,
        lang: str = "ar",
    ) -> str:
        if search_type == "shared":
            if room_min:
                if room_max and room_max > room_min:
                    return (
                        f"From {room_min:,} to {room_max:,} EGP/room"
                        if lang == "en"
                        else f"من {room_min:,} إلى {room_max:,} جنيه/أوضة"
                    )
                return f"{room_min:,} EGP/room" if lang == "en" else f"{room_min:,} جنيه/أوضة"
            return "Price available on request" if lang == "en" else "السعر متاح عند التواصل"

        if monthly_rent:
            return self._price_text(monthly_rent, unit="month" if lang == "en" else "شهر", lang=lang)
        if room_min:
            if room_max and room_max > room_min:
                return (
                    f"From {room_min:,} to {room_max:,} EGP/room"
                    if lang == "en"
                    else f"من {room_min:,} إلى {room_max:,} جنيه/أوضة"
                )
            return f"{room_min:,} EGP/room" if lang == "en" else f"{room_min:,} جنيه/أوضة"
        return "Price available on request" if lang == "en" else "السعر متاح عند التواصل"

    def _price_text(self, amount: int | None, unit: str, lang: str = "ar") -> str:
        if amount:
            return f"{amount:,} EGP/{unit}" if lang == "en" else f"{amount:,} جنيه/{unit}"
        return "Price available on request" if lang == "en" else "السعر متاح عند التواصل"

    def _filter_location(self, filters) -> str | None:
        if not filters:
            return None
        return filters.city or filters.governorate

    def _row_location(
        self,
        city: str | None,
        governorate: str | None,
        street: str | None = None,
        lang: str = "ar",
    ) -> str:
        parts = [part for part in [city, governorate, street] if part]
        separator = ", " if lang == "en" else "، "
        return separator.join(parts) if parts else ("Location not specified" if lang == "en" else "موقع غير محدد")

    def _as_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
