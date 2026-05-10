from sqlalchemy import text
from app.database.connection import engine
from app.models.search_models import SearchFilters


class RoomRepository:

    def search(self, filters: SearchFilters, offset: int = 0, limit: int = 5):
        """يبحث عن الأوض — بحد أقصى 5 نتائج في الصفحة"""

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

        if filters.city:
            conditions.append("p.City = :city")
            params["city"] = filters.city

        if filters.governorate:
            conditions.append("p.Government = :gov")
            params["gov"] = filters.governorate

        if filters.min_price:
            conditions.append("r.Month_rent >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price:
            conditions.append("r.Month_rent <= :max_price")
            params["max_price"] = filters.max_price

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

        if filters.shared_room is True:
            conditions.append("r.Capacity > 1")
        elif filters.shared_room is False:
            conditions.append("r.Capacity = 1")

        if filters.wifi is True:
            conditions.append("pa.Wifi = 1")

        if filters.furnished is True:
            conditions.append("r.Furnished = 1")

        if filters.balcony is True:
            conditions.append("r.Balcony = 1")

        if filters.private_bathroom is True:
            conditions.append("r.EnSuiteBathroom = 1")

        if filters.air_conditioning is True:
            conditions.append("pa.AirConditioning = 1")

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
            r.MinimumStay,
            p.Name AS PropertyName,
            p.City,
            p.Government,
            p.Street,
            pa.Wifi,
            pa.AirConditioning
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
