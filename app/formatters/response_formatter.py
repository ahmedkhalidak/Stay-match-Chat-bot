class ResponseFormatter:
    def format_rooms(self, rooms):
        """Format a list of room dictionaries into a readable Arabic message."""
        if not rooms:
            return "ملقتش أوض مناسبة دلوقتي 😅"

        lines = ["لقيتلك الأوض دي 🛏️"]  # no trailing newline

        for i, room in enumerate(rooms, start=1):
            month_rent = room.get("Month_rent")
            price_text = (
                f"💰 {int(month_rent):,} جنيه / شهر"
                if month_rent
                else "💰 السعر غير متوفر"
            )

            room_name = room.get("RoomName") or "أوضة"
            property_name = room.get("PropertyName") or "غير معروف"
            city = room.get("City") or "غير معروف"
            government = room.get("Government") or "غير معروف"

            lines.append(
                f"{i}. {room_name}\n"
                f"🏠 {property_name}\n"
                f"📍 {city}, {government}\n"
                f"{price_text}"
            )

        return "\n\n".join(lines)  # one blank line between sections

    def format_properties(self, properties):
        """Format a list of property dictionaries into a readable Arabic message."""
        if not properties:
            return "ملقتش شقق مناسبة دلوقتي 😅"

        lines = ["لقيتلك الشقق دي 🏠"]  # no trailing newline

        for i, prop in enumerate(properties, start=1):
            monthly_rent = prop.get("MonthlyRent")
            price_text = (
                f"💰 {int(monthly_rent):,} جنيه / شهر"
                if monthly_rent
                else "💰 السعر غير متوفر"
            )

            name = prop.get("Name") or "شقة"
            city = prop.get("City") or "غير معروف"
            government = prop.get("Government") or "غير معروف"

            lines.append(
                f"{i}. {name}\n"
                f"📍 {city}, {government}\n"
                f"{price_text}"
            )

        return "\n\n".join(lines)