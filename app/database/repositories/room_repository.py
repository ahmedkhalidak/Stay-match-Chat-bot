from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters
from app.utils.location_mapping import location_mapping
from app.utils.logger import debug_log
from app.utils.sql_builder import build_location_conditions


class RoomRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الأوض — بحد أقصى 5 نتائج في الصفحة
        يستخدم OFFSET/FETCH التقليدي (للحفاظ على التوافق)

        FIX — Location: نفس الحل اللي في PropertyRepository.
        بنبحث بـ City = X  OR  Government = X  + كل مدن المحافظة.
        """
        return self._search_with_offset(filters, offset, limit)

    def count(self, filters: SearchFilters) -> int:
        """
        يرجع العدد الكلي للنتائج بدون pagination
        """
        return self._count(filters)

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

        params = {}
        conditions, joins = self._build_where_clause(filters, params)

        # ── Sorting ──────────────────────────────────────────────────────────
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "r.CreatedAt DESC, r.Id DESC"
        if filters.sort_by == "price_low":
            order_clause = "r.Month_rent ASC, r.Id DESC"
        elif filters.sort_by == "price_high":
            order_clause = "r.Month_rent DESC, r.Id DESC"

        join_str = "\n".join(joins)
        where_clause = " AND ".join(conditions)

        debug_log("DB_SEARCH_WHERE", where_clause)
        debug_log("ROOM_SEARCH", f"Executing room search - city={filters.city}, governorate={filters.governorate}")

        query = f"""
        SELECT
            r.Id,
            r.PropertyId,
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
        WHERE {where_clause}
        ORDER BY {order_clause}
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
        """

        debug_log("DB_QUERY", f"Room search - offset={offset}, limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, min_price={filters.min_price}, max_price={filters.max_price}")
        debug_log("ROOM_SQL", query[:500] + "..." if len(query) > 500 else query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} rooms")
            debug_log("ROOM_RESULTS", f"Room search returned {len(rows)} results")

        return rows

    def _count(self, filters: SearchFilters) -> int:
        """
        يرجع العدد الكلي للنتائج بدون pagination
        """
        params = {}
        conditions, joins = self._build_where_clause(filters, params)

        join_str = "\n".join(joins)
        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT COUNT(DISTINCT r.Id) as total
        FROM Rooms r
        {join_str}
        WHERE {where_clause}
        """

        debug_log("DB_COUNT_WHERE", where_clause)
        debug_log("DB_COUNT_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}")
        debug_log("ROOM_SEARCH", f"Counting rooms - city={filters.city}, governorate={filters.governorate}")

        with engine.connect() as conn:
            result = conn.execute(text(query), params).mappings().first()
            count = result["total"] if result else 0
            debug_log("DB_COUNT_RESULT", f"Total rooms: {count}")
            debug_log("ROOM_RESULTS", f"Room count: {count}")

        return count

    def _build_where_clause(self, filters: SearchFilters, params: dict) -> tuple[list[str], list[str]]:
        """
        Builds WHERE conditions and JOINs for room search.
        Returns: (conditions, joins)
        """
        conditions = [
            "p.IsApproved = 1",
            "p.IsDeleted = 0",
            "p.IsRejected = 0",
            "p.IsDraft = 0",
            "r.IsDeleted = 0",
            "r.CapacityAvailable > 0",
        ]

        joins = [
            "JOIN Properties p ON r.PropertyId = p.Id",
            "LEFT JOIN PropertyAmenities pa ON pa.PropertyId = p.Id",
        ]

        # ── Location ─────────────────────────────────────────────────────────
        if filters.city:
            loc_conds = build_location_conditions(filters.city, params, "city", "p")
            conditions.append(f"({' OR '.join(loc_conds)})")

        if filters.governorate:
            loc_conds = build_location_conditions(
                filters.governorate, params, "gov", "p"
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

        # ── Furnished ────────────────────────────────────────────────────────
        if filters.furnished is not None:
            if filters.furnished:
                conditions.append("r.Furnished = 1")
            else:
                conditions.append("r.Furnished = 0")

        # ── Shared / Private ───────────────────────────────────────────────────
        if filters.shared_room is not None:
            if filters.shared_room:
                conditions.append("r.Capacity > 1")
            else:
                conditions.append("r.Capacity = 1")

        # ── Amenities ────────────────────────────────────────────────────────
        if filters.wifi is not None:
            if filters.wifi:
                conditions.append("pa.Wifi = 1")
            else:
                conditions.append("(pa.Wifi = 0 OR pa.Wifi IS NULL)")

        if filters.balcony is not None:
            if filters.balcony:
                conditions.append("r.Balcony = 1")
            else:
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

        return conditions, joins

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

        params = {}
        conditions, joins = self._build_where_clause(filters, params)

        # Cursor condition
        if cursor:
            conditions.append(
                "(r.CreatedAt < :last_created_at OR "
                "(r.CreatedAt = :last_created_at AND r.Id < :last_id))"
            )
            params['last_created_at'] = cursor['created_at']
            params['last_id'] = cursor['id']

        # Sorting
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "r.CreatedAt DESC, r.Id DESC"
        if filters.sort_by == "price_low":
            order_clause = "r.Month_rent ASC, r.Id DESC"
        elif filters.sort_by == "price_high":
            order_clause = "r.Month_rent DESC, r.Id DESC"

        join_str = "\n".join(joins)
        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT
            r.Id,
            r.PropertyId,
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
        WHERE {where_clause}
        ORDER BY {order_clause}
        FETCH NEXT {limit + 1} ROWS ONLY
        """

        debug_log("DB_QUERY", f"Room search with cursor - limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, cursor={cursor}")
        debug_log("ROOM_SEARCH", f"Room search with cursor - city={filters.city}, governorate={filters.governorate}")
        debug_log("ROOM_SQL", query[:500] + "..." if len(query) > 500 else query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} rooms")
            debug_log("ROOM_RESULTS", f"Room search with cursor returned {len(rows)} results")

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