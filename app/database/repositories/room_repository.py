from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters
from app.utils.location_mapping import location_mapping


class RoomRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """يبحث عن الأوض — بحد أقصى 5 نتائج في الصفحة"""

        def _build_gov_conditions(gov_name: str, params: dict, prefix: str) -> list[str]:
            """Build SQL conditions for a governorate including all its cities."""
            conditions = [f"p.Government = :{prefix}_gov"]
            params[f"{prefix}_gov"] = gov_name

            cities = location_mapping.get_cities(gov_name)
            if cities:
                city_placeholders = []
                for i, city in enumerate(cities):
                    param_key = f"{prefix}_city_{i}"
                    params[param_key] = city
                    city_placeholders.append(f":{param_key}")
                conditions.append(f"p.City IN ({', '.join(city_placeholders)})")

            return conditions

        conditions = [
            "p.IsApproved = 1",
            "p.IsDeleted = 0",
            "p.IsRejected = 0",
            "p.IsDraft = 0",
            "r.IsDeleted = 0",
            "r.CapacityAvailable > 0",
        ]

        params = {}
        joins = [
            "JOIN Properties p ON r.PropertyId = p.Id",
            "LEFT JOIN PropertyAmenities pa ON pa.PropertyId = p.Id",
        ]

        # ── Location (dynamic governorate-city mapping for ALL governorates) ─
        if filters.city:
            city_conditions = ["p.City = :city"]
            params["city"] = filters.city

            # Check if city name is actually a governorate name (e.g. "Cairo", "Ismailia")
            gov_for_city = location_mapping.get_governorate(filters.city)
            if gov_for_city and gov_for_city.lower() == filters.city.lower():
                city_conditions = _build_gov_conditions(gov_for_city, params, "city_gov")

            conditions.append(f"({' OR '.join(city_conditions)})")

        if filters.governorate:
            # Every governorate includes all its cities dynamically
            gov_conditions = _build_gov_conditions(filters.governorate, params, "gov")
            conditions.append(f"({' OR '.join(gov_conditions)})")

        # ── Price ────────────────────────────────
        if filters.min_price:
            conditions.append("r.Month_rent >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price:
            conditions.append("r.Month_rent <= :max_price")
            params["max_price"] = filters.max_price

        # ── Tenant type & Gender ─────────────────
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.RoomId = r.Id")

        if filters.tenant_type == "student":
            conditions.append("at.AllowsStudents = 1")
        elif filters.tenant_type == "worker":
            conditions.append("at.AllowsWorkers = 1")

        if filters.gender == "male":
            conditions.append("(at.StudentGender = 0 OR at.WorkerGender = 0 OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))")
        elif filters.gender == "female":
            conditions.append("(at.StudentGender = 1 OR at.WorkerGender = 1 OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))")

        # ── Shared / Private ─────────────────────
        if filters.shared_room is True:
            conditions.append("r.Capacity > 1")
        elif filters.shared_room is False:
            conditions.append("r.Capacity = 1")

        # ── Amenities ────────────────────────────
        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")
        elif filters.wifi is False:
            conditions.append("(pa.Wifi = 0 OR pa.Wifi IS NULL)")

        if filters.furnished is True:
            conditions.append("r.Furnished = 1")
        elif filters.furnished is False:
            conditions.append("(r.Furnished = 0 OR r.Furnished IS NULL)")

        if filters.balcony is True:
            conditions.append("r.Balcony = 1")
        elif filters.balcony is False:
            conditions.append("(r.Balcony = 0 OR r.Balcony IS NULL)")

        if filters.private_bathroom is True:
            conditions.append("r.EnSuiteBathroom = 1")
        elif filters.private_bathroom is False:
            conditions.append("(r.EnSuiteBathroom = 0 OR r.EnSuiteBathroom IS NULL)")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")
        elif filters.air_conditioning is False:
            conditions.append("(pa.AirConditioning = 0 OR pa.AirConditioning IS NULL)")

        # ── Sorting ──────────────────────────────
        order_clause = "r.CreatedAt DESC"

        if filters.sort_by == "price_low":
            order_clause = "r.Month_rent ASC"
        elif filters.sort_by == "price_high":
            order_clause = "r.Month_rent DESC"

        join_str = "\n".join(joins)

        query = f"""
        SELECT
            r.Id,
            r.RoomName,
            r.Month_rent,
            r.Deposit,
            r.Capacity,
            r.CapacityAvailable,
            r.Furnished,
            r.Balcony,
            r.EnSuiteBathroom,
            r.SharedBathroom,
            r.Window,
            r.PetsAllowed,
            r.MinimumStay,

            p.Name AS PropertyName,
            p.City,
            p.Government,
            p.NumberOfBedrooms,
            p.NumberOfGuestBathrooms,
            p.Street,

            pa.Wifi,
            pa.AirConditioning,
            pa.Tv,
            pa.Washer,
            pa.Refrigerator,
            pa.FreeParking

        FROM Rooms r
        {join_str}
        WHERE {' AND '.join(conditions)}
        ORDER BY {order_clause}
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
        """

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        return rows
