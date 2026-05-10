from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters


class PropertyRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """يبحث عن الشقق — بحد أقصى 5 نتائج في الصفحة"""

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

        if filters.city:
            conditions.append("p.City = :city")
            params["city"] = filters.city

        if filters.governorate:
            conditions.append("p.Government = :gov")
            params["gov"] = filters.governorate

        if filters.min_price:
            conditions.append("COALESCE(p.MonthlyRent, r.Month_rent) >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price:
            conditions.append("COALESCE(p.MonthlyRent, r.Month_rent) <= :max_price")
            params["max_price"] = filters.max_price

        if filters.furnished is True:
            conditions.append("p.Furnished = 1")

        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")

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

        order_clause = "p.CreatedAt DESC"
        if filters.sort_by == "price_low":
            order_clause = "COALESCE(p.MonthlyRent, MIN(r.Month_rent)) ASC"
        elif filters.sort_by == "price_high":
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
            MIN(r.Month_rent) AS RoomMinPrice,
            MAX(r.Month_rent) AS RoomMaxPrice,
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
                 pa.Wifi, pa.AirConditioning, pa.Tv, pa.Washer, pa.Refrigerator, pa.FreeParking
        ORDER BY {order_clause}
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
        """

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        return rows
