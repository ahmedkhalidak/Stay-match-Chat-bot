class ResponseFormatter:
    """
    Formatter ب tone مصري friendly
    بيرجع بيانات منظمة: ID واضح + أهم التفاصيل بس
    """

    def format_rooms(self, rooms, filters=None, expanded=False, has_more=False, page_num=1) -> str:
        if not rooms:
            return (
                "مش لاقي أوض بالمواصفات دي حالياً 😅\n"
                "جرب تغيّر المدينة أو السعر وقولي تاني!"
            )

        lines = []
        total_label = f"صفحة {page_num}" if page_num > 1 else ""
        header = f"🏠 لقيتلك {len(rooms)} أوضة"
        if total_label:
            header += f" ({total_label})"
        if expanded:
            header += " — بعد ما وسّعتلك البحث شوية"
        lines.append(header)
        lines.append("═" * 30)

        for room in rooms:
            rid = room.get("Id", "?")
            name = room.get("RoomName") or "أوضة"
            prop = room.get("PropertyName") or "عقار"
            city = room.get("City") or ""
            gov = room.get("Government") or ""
            street = room.get("Street", "")

            # Location line
            loc_parts = [p for p in [city, gov] if p]
            location = ", ".join(loc_parts) if loc_parts else "موقع غير محدد"
            if street:
                location += f" — {street}"

            # Price
            rent = room.get("Month_rent")
            if rent is not None and rent > 0:
                price = f"💰 {int(rent):,} جنيه/شهر"
            else:
                price = "💰 السعر غير متاح"

            deposit = room.get("Deposit")
            deposit_line = f"🔑 تأمين: {int(deposit):,} جنيه" if deposit else ""

            # Badges - أهم الحاجات بس
            badges = []
            cap = room.get("Capacity", 1)
            cap_avail = room.get("CapacityAvailable", 0)
            if cap and cap > 1:
                badges.append(f"👥 مشتركة ({cap_avail}/{cap})")
            else:
                badges.append("🔒 سنجل")

            if room.get("Furnished"):
                badges.append("🛋️ مفروشة")
            if room.get("Wifi"):
                badges.append("📶 واي فاي")
            if room.get("AirConditioning"):
                badges.append("❄️ تكييف")
            if room.get("Balcony"):
                badges.append("🌿 بلكونة")
            if room.get("EnSuiteBathroom"):
                badges.append("🚿 حمام خاص")

            min_stay = room.get("MinimumStay")
            if min_stay:
                badges.append(f"📅 {min_stay} شهر")

            badges_str = "  ".join(badges)

            block = (
                f"\n🆔 #{rid}\n"
                f"📌 {name}\n"
                f"🏢 {prop}\n"
                f"📍 {location}\n"
                f"{price}"
            )
            if deposit_line:
                block += f"\n{deposit_line}"
            block += f"\n{badges_str}"

            lines.append(block)

        lines.append("\n" + "═" * 30)

        if has_more:
            lines.append("➡️ عايز تشوف كمان؟ قولي \"المزيد\" أو \"كمان\"")
        elif page_num > 1:
            lines.append("✅ دي كانت آخر النتائج")

        lines.append(f"\n💬 {self._get_smart_suggestion(filters, 'room')}")
        return "\n".join(lines)

    def format_properties(self, properties, filters=None, expanded=False, has_more=False, page_num=1) -> str:
        if not properties:
            return (
                "مش لاقي شقق بالمواصفات دي حالياً 😅\n"
                "جرب تغيّر المدينة أو السعر وقولي تاني!"
            )

        lines = []
        total_label = f"صفحة {page_num}" if page_num > 1 else ""
        header = f"🏠 لقيتلك {len(properties)} شقة"
        if total_label:
            header += f" ({total_label})"
        if expanded:
            header += " — بعد ما وسّعتلك البحث شوية"
        lines.append(header)
        lines.append("═" * 30)

        for prop in properties:
            pid = prop.get("Id", "?")
            name = prop.get("Name") or "شقة"
            city = prop.get("City") or ""
            gov = prop.get("Government") or ""

            loc_parts = [p for p in [city, gov] if p]
            location = ", ".join(loc_parts) if loc_parts else "موقع غير محدد"

            # Price
            rent = prop.get("MonthlyRent")
            if rent is not None and rent > 0:
                price = f"💰 {int(rent):,} جنيه/شهر"
            else:
                price = "💰 السعر غير متاح"

            deposit = prop.get("Deposite")
            deposit_line = f"🔑 تأمين: {int(deposit):,} جنيه" if deposit else ""

            # Details - أهم الحاجات بس
            details = []
            total_rooms = prop.get("TotalRooms")
            avail_rooms = prop.get("AvailableRooms")
            if total_rooms:
                details.append(f"🚪 {total_rooms} غرف")
            if avail_rooms is not None:
                details.append(f"✅ {avail_rooms} متاحة")
            size = prop.get("Size")
            if size:
                details.append(f"📐 {int(size)} م²")

            if prop.get("Furnished"):
                details.append("🛋️ مفروشة")
            if prop.get("Wifi"):
                details.append("📶 واي فاي")
            if prop.get("AirConditioning"):
                details.append("❄️ تكييف")
            if prop.get("FreeParking"):
                details.append("🚗 موقف")

            min_stay = prop.get("MinimumStay")
            if min_stay:
                details.append(f"📅 {min_stay} شهر")

            details_str = "  ".join(details)

            block = (
                f"\n🆔 #{pid}\n"
                f"📌 {name}\n"
                f"📍 {location}\n"
                f"{price}"
            )
            if deposit_line:
                block += f"\n{deposit_line}"
            block += f"\n{details_str}"

            lines.append(block)

        lines.append("\n" + "═" * 30)

        if has_more:
            lines.append("➡️ عايز تشوف كمان؟ قولي \"المزيد\" أو \"كمان\"")
        elif page_num > 1:
            lines.append("✅ دي كانت آخر النتائج")

        lines.append(f"\n💬 {self._get_smart_suggestion(filters, 'property')}")
        return "\n".join(lines)

    def _get_smart_suggestion(self, filters, search_type: str) -> str:
        """اقتراح ذكي بناءً على الفلاتر الحالية"""
        if not filters:
            return "قولي لو عايز تصفية تانية أو مدينة مختلفة! 👇"

        suggestions = []

        if not filters.city:
            suggestions.append('"في القاهرة"')
            suggestions.append('"في إسماعيلية"')

        if not filters.max_price and not filters.min_price:
            suggestions.append('"تحت 5000"')

        if not filters.sort_by:
            suggestions.append('"أرخص"')

        if search_type == "room":
            if not filters.wifi:
                suggestions.append('"فيها واي فاي"')
            if not filters.air_conditioning:
                suggestions.append('"فيها تكييف"')

        if not filters.furnished:
            suggestions.append('"مفروشة"')

        if not filters.tenant_type:
            suggestions.append('"للطلاب"')

        if not filters.gender:
            suggestions.append('"شباب"')
            suggestions.append('"بنات"')

        if suggestions:
            return f"ممكن تجرب: {', '.join(suggestions[:4])}"
        return "قولي لو عايز تغيّر حاجة في البحث! 👇"
