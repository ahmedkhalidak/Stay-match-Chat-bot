from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters
from app.utils.location_mapping import location_mapping
from app.utils.logger import debug_log


class RoomRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الأوض — بحد أقصى 5 نتائج في الصفحة
        يستخدم OFFSET/FETCH التقليدي (للحفاظ على التوافق)

        FIX — Location: نفس الحل اللي في PropertyRepository.
        بنبحث بـ City = X  OR  Government = X  + كل مدن المحافظة.
        """
        return self._search_with_offset(filters, offset, limit)

    def search_with_cursor(
        self,
        filters: SearchFilters,
        cursor: dict = None,
        limit: int = 5
    ):
        """
        يبحث عن الأوض باستخدام cursor-based pagination
        cursor: {'created_at': '2024-01-01T00:00:00', 'id': 123}
        """
        return self._search_with_cursor(filters, cursor, limit)

    def _search_with_offset(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الأوض — بحد أقصى 5 نتائج في الصفحة

        FIX — Location: نفس الحل اللي في PropertyRepository.
        بنبحث بـ City = X  OR  Government = X  + كل مدن المحافظة.
        """

        def _build_location_conditions(
            name: str, params: dict, prefix: str
        ) -> list[str]:
            """
            Enhanced location conditions with case-insensitive and partial matching.
            Limit to first 20 cities to avoid FreeTDS parameter limit.
            """
            conds = [
                f"LOWER(p.City) = LOWER(:{prefix}_name)",
                f"LOWER(p.Government) = LOWER(:{prefix}_name)",
                f"p.City LIKE :{prefix}_name_like",
                f"p.Government LIKE :{prefix}_name_like",
            ]
            params[f"{prefix}_name"] = name
            params[f"{prefix}_name_like"] = f"%{name}%"

            # Limit to first 20 cities to avoid FreeTDS parameter limit
            cities = location_mapping.get_cities(name)
            if cities:
                cities = cities[:20]
                placeholders = []
                for i, city in enumerate(cities):
                    key = f"{prefix}_c{i}"
                    params[key] = city
                    placeholders.append(f":{key}")
                conds.append(f"p.City IN ({', '.join(placeholders)})")

            return conds

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

        # ── Location ─────────────────────────────────────────────────────────
        if filters.city:
            loc_conds = _build_location_conditions(filters.city, params, "city")
            conditions.append(f"({' OR '.join(loc_conds)})")

        if filters.governorate:
            loc_conds = _build_location_conditions(
                filters.governorate, params, "gov"
            )
            conditions.append(f"({' OR '.join(loc_conds)})")

        # ── Price ─────────────────────────────────────────────────────────────
        if filters.min_price is not None:
            conditions.append("r.Month_rent >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price is not None:
            conditions.append("r.Month_rent <= :max_price")
            params["max_price"] = filters.max_price

        # ── Tenant type & Gender ──────────────────────────────────────────────
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.RoomId = r.Id")

        if filters.tenant_type == "student":
            conditions.append("at.AllowsStudents = 1")
        elif filters.tenant_type == "worker":
            conditions.append("at.AllowsWorkers = 1")

        if filters.gender == "male":
            conditions.append(
                "(at.StudentGender = 0 OR at.WorkerGender = 0 "
                "OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))"
            )
        elif filters.gender == "female":
            conditions.append(
                "(at.StudentGender = 1 OR at.WorkerGender = 1 "
                "OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))"
            )

        # ── Shared / Private ──────────────────────────────────────────────────
        if filters.shared_room is True:
            conditions.append("r.Capacity > 1")
        elif filters.shared_room is False:
            conditions.append("r.Capacity = 1")

        # ── Amenities ─────────────────────────────────────────────────────────
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
            conditions.append(
                "(pa.AirConditioning = 0 OR pa.AirConditioning IS NULL)"
            )

        # ── Sorting ───────────────────────────────────────────────────────────
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "r.CreatedAt DESC, r.Id DESC"
        if filters.sort_by == "price_low":
            order_clause = "r.Month_rent ASC, r.Id DESC"
        elif filters.sort_by == "price_high":
            order_clause = "r.Month_rent DESC, r.Id DESC"

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

            p.Name        AS PropertyName,
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

        debug_log("DB_QUERY", f"Room search - offset={offset}, limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, min_price={filters.min_price}, max_price={filters.max_price}")
        debug_log("DB_SQL", query[:200] + "..." if len(query) > 200 else query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} rooms")

        return rows

    def _search_with_cursor(
        self,
        filters: SearchFilters,
        cursor: dict = None,
        limit: int = 5
    ):
        """
        البحث باستخدام cursor-based pagination
        cursor: {'created_at': '2024-01-01T00:00:00', 'id': 123}
        """

        def _build_location_conditions(
            name: str, params: dict, prefix: str
        ) -> list[str]:
            conds = [
                f"LOWER(p.City) = LOWER(:{prefix}_name)",
                f"LOWER(p.Government) = LOWER(:{prefix}_name)",
                f"p.City LIKE :{prefix}_name_like",
                f"p.Government LIKE :{prefix}_name_like",
            ]
            params[f"{prefix}_name"] = name
            params[f"{prefix}_name_like"] = f"%{name}%"

            # Limit to first 20 cities to avoid FreeTDS parameter limit
            cities = location_mapping.get_cities(name)
            if cities:
                cities = cities[:20]
                placeholders = []
                for i, city in enumerate(cities):
                    key = f"{prefix}_c{i}"
                    params[key] = city
                    placeholders.append(f":{key}")
                conds.append(f"p.City IN ({', '.join(placeholders)})")

            return conds

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

        # Cursor condition
        if cursor:
            conditions.append(
                "(r.CreatedAt < :last_created_at OR "
                "(r.CreatedAt = :last_created_at AND r.Id < :last_id))"
            )
            params['last_created_at'] = cursor['created_at']
            params['last_id'] = cursor['id']

        # Location
        if filters.city:
            loc_conds = _build_location_conditions(filters.city, params, "city")
            conditions.append(f"({' OR '.join(loc_conds)})")

        if filters.governorate:
            loc_conds = _build_location_conditions(
                filters.governorate, params, "gov"
            )
            conditions.append(f"({' OR '.join(loc_conds)})")

        # Price
        if filters.min_price is not None:
            conditions.append("r.Month_rent >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price is not None:
            conditions.append("r.Month_rent <= :max_price")
            params["max_price"] = filters.max_price

        # Tenant type & Gender
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.RoomId = r.Id")

        if filters.tenant_type == "student":
            conditions.append("at.AllowsStudents = 1")
        elif filters.tenant_type == "worker":
            conditions.append("at.AllowsWorkers = 1")

        if filters.gender == "male":
            conditions.append(
                "(at.StudentGender = 0 OR at.WorkerGender = 0 "
                "OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))"
            )
        elif filters.gender == "female":
            conditions.append(
                "(at.StudentGender = 1 OR at.WorkerGender = 1 "
                "OR (at.StudentGender IS NULL AND at.WorkerGender IS NULL))"
            )

        # Shared / Private
        if filters.shared_room is True:
            conditions.append("r.Capacity > 1")
        elif filters.shared_room is False:
            conditions.append("r.Capacity = 1")

        # Amenities
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
            conditions.append(
                "(pa.AirConditioning = 0 OR pa.AirConditioning IS NULL)"
            )

        # Sorting
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "r.CreatedAt DESC, r.Id DESC"
        if filters.sort_by == "price_low":
            order_clause = "r.Month_rent ASC, r.Id DESC"
        elif filters.sort_by == "price_high":
            order_clause = "r.Month_rent DESC, r.Id DESC"

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
            r.CreatedAt,

            p.Name        AS PropertyName,
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
        FETCH NEXT {limit + 1} ROWS ONLY
        """

        debug_log("DB_QUERY", f"Room search with cursor - limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, cursor={cursor}")
        debug_log("DB_SQL", query[:200] + "..." if len(query) > 200 else query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} rooms")

        # Determine if there are more results
        has_more = len(rows) > limit
        results = rows[:limit]

        # Create next cursor
        next_cursor = None
        if has_more and results:
            last_result = results[-1]
            next_cursor = {
                'created_at': last_result['CreatedAt'].isoformat() if last_result['CreatedAt'] else None,
                'id': last_result['Id']
            }

        return results, next_cursor, has_more