from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters
from app.utils.location_mapping import location_mapping


class PropertyRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الشقق — بحد أقصى 5 نتائج في الصفحة

        ٣ أنواع:
        - property: كل الشقق (كاملة + مشتركة)
        - full: شقة كاملة بس (MonthlyRent IS NOT NULL)
        - shared: شقة مشتركة بس (MonthlyRent IS NULL + فيها أوض)

        خاصية: أي محافظة بتشمل كل مدنها التابعة
        """

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
            "p.PropertyType = 1",
        ]

        params = {}
        joins = [
            "LEFT JOIN PropertyAmenities pa ON pa.PropertyId = p.Id",
            "LEFT JOIN Rooms r ON r.PropertyId = p.Id AND r.IsDeleted = 0",
        ]

        # ── Search Type Filter ───────────────────
        if filters.search_type == "full":
            conditions.append("p.MonthlyRent IS NOT NULL")
        elif filters.search_type == "shared":
            conditions.append("p.MonthlyRent IS NULL")
            conditions.append("EXISTS (SELECT 1 FROM Rooms r2 WHERE r2.PropertyId = p.Id AND r2.IsDeleted = 0)")

        # ── Location (dynamic governorate-city mapping for ALL governorates) ─
        if filters.city:
            city_conditions = ["p.City = :city"]
            params["city"] = filters.city

            # Check if city name is actually a governorate name (e.g. "Cairo", "Ismailia")
            # If so, search across all cities in that governorate
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
            if filters.search_type == "shared":
                conditions.append("r.Month_rent >= :min_price")
            else:
                conditions.append("COALESCE(p.MonthlyRent, r.Month_rent) >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price:
            if filters.search_type == "shared":
                conditions.append("r.Month_rent <= :max_price")
            else:
                conditions.append("COALESCE(p.MonthlyRent, r.Month_rent) <= :max_price")
            params["max_price"] = filters.max_price

        # ── Furnished ────────────────────────────
        if filters.furnished is True:
            conditions.append("p.Furnished = 1")

        # ── Amenities ────────────────────────────
        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")

        # ── Tenant type & Gender ─────────────────
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.PropertyId = p.Id")

        if filters.tenant_type == "student":
            conditions.append("at.AllowsStudents = 1")
        elif filters.tenant_type == "worker":
            conditions.append("at.AllowsWorkers = 1")

        if filters.gender == "male":
            conditions.append("(at.StudentGender = 0 OR at.WorkerGender = 0 OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))")
        elif filters.gender == "female":
            conditions.append("(at.StudentGender = 1 OR at.WorkerGender = 1 OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))")

        # ── Sorting ─────────────────────────────
        order_clause = "p.CreatedAt DESC"
        if filters.sort_by == "price_low":
            if filters.search_type == "shared":
                order_clause = "MIN(r.Month_rent) ASC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MIN(r.Month_rent)) ASC"
        elif filters.sort_by == "price_high":
            if filters.search_type == "shared":
                order_clause = "MAX(r.Month_rent) DESC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MAX(r.Month_rent)) DESC"

        join_str = "\n".join(joins)

        query = f"""
        SELECT
            p.Id,
            p.Name,
            p.MonthlyRent,
            p.Deposite,
            p.City,
            p.Government,
            p.Description,
            p.NumberOfBedrooms,
            p.NumberOfLivingRooms,
            p.TotalRooms,
            p.AvailableRooms,
            p.Furnished,
            p.Size,
            p.MinimumStay,
            COUNT(r.Id) AS TotalRoomsCount,
            MIN(r.Month_rent) AS RoomMinPrice,
            MAX(r.Month_rent) AS RoomMaxPrice,
            AVG(r.Month_rent) AS RoomAvgPrice,
            pa.Wifi,
            pa.AirConditioning,
            pa.Tv,
            pa.Washer,
            pa.Refrigerator,
            pa.FreeParking
        FROM Properties p
        {join_str}
        WHERE {' AND '.join(conditions)}
        GROUP BY p.Id, p.Name, p.MonthlyRent, p.Deposite, p.City, p.Government,
                 p.Description, p.NumberOfBedrooms, p.NumberOfLivingRooms, p.TotalRooms,
                 p.AvailableRooms, p.Furnished, p.Size, p.MinimumStay,
                 pa.Wifi, pa.AirConditioning, pa.Tv, pa.Washer, pa.Refrigerator, pa.FreeParking,
                 p.CreatedAt
        ORDER BY {order_clause}
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
        """

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        return rows
