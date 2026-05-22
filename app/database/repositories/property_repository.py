from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters
from app.utils.location_mapping import location_mapping
from app.utils.logger import debug_log


class PropertyRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الشقق — بحد أقصى 5 نتائج في الصفحة
        يستخدم OFFSET/FETCH التقليدي (للحفاظ على التوافق)

        ٣ أنواع:
        - property: كل الشقق (كاملة + مشتركة)
        - full:     شقة كاملة بس (MonthlyRent IS NOT NULL)
        - shared:   شقة مشتركة بس (MonthlyRent IS NULL + فيها أوض)
        """
        return self._search_with_offset(filters, offset, limit)

    def search_with_cursor(
        self, 
        filters: SearchFilters, 
        cursor: dict = None, 
        limit: int = 5
    ):
        """
        يبحث عن الشقق باستخدام cursor-based pagination
        cursor: {'created_at': '2024-01-01T00:00:00', 'id': 123}
        
        هذا الأسلوب أسرع بكثير للبيانات الكبيرة لأنه لا يستخدم OFFSET
        """
        return self._search_with_cursor(filters, cursor, limit)

    def _search_with_offset(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """
        يبحث عن الشقق — بحد أقصى 5 نتائج في الصفحة

        ٣ أنواع:
        - property: كل الشقق (كاملة + مشتركة)
        - full:     شقة كاملة بس (MonthlyRent IS NOT NULL)
        - shared:   شقة مشتركة بس (MonthlyRent IS NULL + فيها أوض)

        FIX #1 — Location:
            لما city جاي من الـ NLP بيبقى اسم المحافظة أحياناً (e.g. "Ismailia").
            الكود القديم كان بيتحقق بـ exact lowercase match وده بيفشل كتير.
            الحل: نبحث دايماً بـ City = X  OR  Government = X  بالإضافة لكل
            المدن التابعة للمحافظة دي لو موجودة.

        FIX #2 — search_type "property":
            القديم كان بيسيب "property" من غير أي filter على MonthlyRent
            فكان بيخلط بين شقق كاملة ومشتركة.
            الحل: "property" = بحث عام يشمل الاتنين بدون تقييد.
        """

        def _build_location_conditions(
            name: str, params: dict, prefix: str
        ) -> list[str]:
            """
            يبني conditions شاملة للـ location:
            - City = name (case-insensitive)
            - Government = name (case-insensitive)
            - City LIKE name (partial match)
            - Government LIKE name (partial match)
            - لو name دي محافظة معروفة → City IN (أول 20 مدينة فقط لتجنب حد المعاملات)
            """
            conds = [
                f"LOWER(p.City) = LOWER(:{prefix}_name)",
                f"LOWER(p.Government) = LOWER(:{prefix}_name)",
                f"p.City LIKE :{prefix}_name_like",
                f"p.Government LIKE :{prefix}_name_like",
            ]
            params[f"{prefix}_name"] = name
            params[f"{prefix}_name_like"] = f"%{name}%"

            # لو الاسم ده محافظة فعلاً → ضيف أول 20 مدينة فقط
            # FreeTDS لديه حد أقصى لعدد المعاملات
            cities = location_mapping.get_cities(name)
            if cities:
                # Limit to first 20 cities to avoid parameter limit
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
        ]

        params = {}
        joins = [
            "LEFT JOIN PropertyAmenities pa ON pa.PropertyId = p.Id",
            "LEFT JOIN Rooms r ON r.PropertyId = p.Id AND r.IsDeleted = 0",
        ]

        # ── Search Type Filter ──────────────────────────────────────────────
        if filters.search_type == "full":
            # شقة كاملة: PropertyType = 1 + MonthlyRent IS NOT NULL
            conditions.append("p.PropertyType = 1")
            conditions.append("p.MonthlyRent IS NOT NULL")

        elif filters.search_type == "shared":
            # شقة مشتركة/غرف: PropertyType = 0 + MonthlyRent IS NULL
            conditions.append("p.PropertyType = 0")
            conditions.append("p.MonthlyRent IS NULL")
            conditions.append(
                "EXISTS (SELECT 1 FROM Rooms r2 "
                "WHERE r2.PropertyId = p.Id AND r2.IsDeleted = 0)"
            )

        elif filters.search_type == "property":
            # شقق عامة: PropertyType IN (0, 1)
            conditions.append("p.PropertyType IN (0, 1)")

        # ── Location ────────────────────────────────────────────────────────
        # FIX: بنستخدم _build_location_conditions اللي بتشمل City + Government
        #      + كل مدن المحافظة في نفس الوقت.
        if filters.city:
            loc_conds = _build_location_conditions(filters.city, params, "city")
            conditions.append(f"({' OR '.join(loc_conds)})")

        if filters.governorate:
            loc_conds = _build_location_conditions(
                filters.governorate, params, "gov"
            )
            conditions.append(f"({' OR '.join(loc_conds)})")

        # ── Price ────────────────────────────────────────────────────────────
        if filters.min_price is not None:
            if filters.search_type == "shared":
                conditions.append("r.Month_rent >= :min_price")
            else:
                conditions.append(
                    "COALESCE(p.MonthlyRent, r.Month_rent) >= :min_price"
                )
            params["min_price"] = filters.min_price

        if filters.max_price is not None:
            if filters.search_type == "shared":
                conditions.append("r.Month_rent <= :max_price")
            else:
                conditions.append(
                    "COALESCE(p.MonthlyRent, r.Month_rent) <= :max_price"
                )
            params["max_price"] = filters.max_price

        # ── Furnished ────────────────────────────────────────────────────────
        if filters.furnished is True:
            conditions.append("p.Furnished = 1")
        elif filters.furnished is False:
            conditions.append("(p.Furnished = 0 OR p.Furnished IS NULL)")

        # ── Amenities ────────────────────────────────────────────────────────
        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")
        elif filters.wifi is False:
            conditions.append("(pa.Wifi = 0 OR pa.Wifi IS NULL)")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")
        elif filters.air_conditioning is False:
            conditions.append("(pa.AirConditioning = 0 OR pa.AirConditioning IS NULL)")

        # ── Tenant type & Gender ─────────────────────────────────────────────
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.PropertyId = p.Id")

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

        # ── Sorting ──────────────────────────────────────────────────────────
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "p.CreatedAt DESC, p.Id DESC"
        if filters.sort_by == "price_low":
            if filters.search_type == "shared":
                order_clause = "MIN(r.Month_rent) ASC, p.Id DESC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MIN(r.Month_rent)) ASC, p.Id DESC"
        elif filters.sort_by == "price_high":
            if filters.search_type == "shared":
                order_clause = "MAX(r.Month_rent) DESC, p.Id DESC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MAX(r.Month_rent)) DESC, p.Id DESC"

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
            COUNT(r.Id)          AS TotalRoomsCount,
            MIN(r.Month_rent)    AS RoomMinPrice,
            MAX(r.Month_rent)    AS RoomMaxPrice,
            AVG(r.Month_rent)    AS RoomAvgPrice,
            pa.Wifi,
            pa.AirConditioning,
            pa.Tv,
            pa.Washer,
            pa.Refrigerator,
            pa.FreeParking
        FROM Properties p
        {join_str}
        WHERE {' AND '.join(conditions)}
        GROUP BY
            p.Id, p.Name, p.MonthlyRent, p.Deposite, p.City, p.Government,
            p.Description, p.NumberOfBedrooms, p.NumberOfLivingRooms,
            p.TotalRooms, p.AvailableRooms, p.Furnished, p.Size, p.MinimumStay,
            pa.Wifi, pa.AirConditioning, pa.Tv, pa.Washer,
            pa.Refrigerator, pa.FreeParking, p.CreatedAt
        ORDER BY {order_clause}
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
        """

        debug_log("DB_QUERY", f"Property search - offset={offset}, limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, min_price={filters.min_price}, max_price={filters.max_price}")
        debug_log("DB_SQL", query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} properties")

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
        ]

        params = {}
        joins = [
            "LEFT JOIN PropertyAmenities pa ON pa.PropertyId = p.Id",
            "LEFT JOIN Rooms r ON r.PropertyId = p.Id AND r.IsDeleted = 0",
        ]

        # Cursor condition
        if cursor:
            conditions.append(
                "(p.CreatedAt < :last_created_at OR "
                "(p.CreatedAt = :last_created_at AND p.Id < :last_id))"
            )
            params['last_created_at'] = cursor['created_at']
            params['last_id'] = cursor['id']

        # Search Type Filter
        if filters.search_type == "full":
            # شقة كاملة: PropertyType = 1 + MonthlyRent IS NOT NULL
            conditions.append("p.PropertyType = 1")
            conditions.append("p.MonthlyRent IS NOT NULL")
        elif filters.search_type == "shared":
            # شقة مشتركة/غرف: PropertyType = 0 + MonthlyRent IS NULL
            conditions.append("p.PropertyType = 0")
            conditions.append("p.MonthlyRent IS NULL")
            conditions.append(
                "EXISTS (SELECT 1 FROM Rooms r2 "
                "WHERE r2.PropertyId = p.Id AND r2.IsDeleted = 0)"
            )
        elif filters.search_type == "property":
            # شقق عامة: PropertyType IN (0, 1)
            conditions.append("p.PropertyType IN (0, 1)")

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
            if filters.search_type == "shared":
                conditions.append("r.Month_rent >= :min_price")
            else:
                conditions.append(
                    "COALESCE(p.MonthlyRent, r.Month_rent) >= :min_price"
                )
            params["min_price"] = filters.min_price

        if filters.max_price is not None:
            if filters.search_type == "shared":
                conditions.append("r.Month_rent <= :max_price")
            else:
                conditions.append(
                    "COALESCE(p.MonthlyRent, r.Month_rent) <= :max_price"
                )
            params["max_price"] = filters.max_price

        # Furnished
        if filters.furnished is True:
            conditions.append("p.Furnished = 1")
        elif filters.furnished is False:
            conditions.append("(p.Furnished = 0 OR p.Furnished IS NULL)")

        # Amenities
        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")
        elif filters.wifi is False:
            conditions.append("(pa.Wifi = 0 OR pa.Wifi IS NULL)")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")
        elif filters.air_conditioning is False:
            conditions.append("(pa.AirConditioning = 0 OR pa.AirConditioning IS NULL)")

        # Tenant type & Gender
        if filters.tenant_type or filters.gender:
            joins.append("LEFT JOIN AllowedTenants at ON at.PropertyId = p.Id")

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

        # Sorting
        # Add Id as secondary sort for deterministic pagination (fixes duplicate results)
        order_clause = "p.CreatedAt DESC, p.Id DESC"
        if filters.sort_by == "price_low":
            if filters.search_type == "shared":
                order_clause = "MIN(r.Month_rent) ASC, p.Id DESC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MIN(r.Month_rent)) ASC, p.Id DESC"
        elif filters.sort_by == "price_high":
            if filters.search_type == "shared":
                order_clause = "MAX(r.Month_rent) DESC, p.Id DESC"
            else:
                order_clause = "COALESCE(p.MonthlyRent, MAX(r.Month_rent)) DESC, p.Id DESC"

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
            p.CreatedAt,
            COUNT(r.Id)          AS TotalRoomsCount,
            MIN(r.Month_rent)    AS RoomMinPrice,
            MAX(r.Month_rent)    AS RoomMaxPrice,
            AVG(r.Month_rent)    AS RoomAvgPrice,
            pa.Wifi,
            pa.AirConditioning,
            pa.Tv,
            pa.Washer,
            pa.Refrigerator,
            pa.FreeParking
        FROM Properties p
        {join_str}
        WHERE {' AND '.join(conditions)}
        GROUP BY
            p.Id, p.Name, p.MonthlyRent, p.Deposite, p.City, p.Government,
            p.Description, p.NumberOfBedrooms, p.NumberOfLivingRooms,
            p.TotalRooms, p.AvailableRooms, p.Furnished, p.Size, p.MinimumStay,
            p.CreatedAt,
            pa.Wifi, pa.AirConditioning, pa.Tv, pa.Washer,
            pa.Refrigerator, pa.FreeParking
        ORDER BY {order_clause}
        FETCH NEXT {limit + 1} ROWS ONLY
        """

        debug_log("DB_QUERY", f"Property search with cursor - limit={limit}")
        debug_log("DB_PARAMS", f"Filters: city={filters.city}, governorate={filters.governorate}, cursor={cursor}")
        debug_log("DB_SQL", query)

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            debug_log("DB_RESULTS", f"Found {len(rows)} properties")

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