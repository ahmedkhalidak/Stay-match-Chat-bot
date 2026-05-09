from sqlalchemy import text

from app.database.connection import engine
from app.models.search_models import SearchFilters


class RoomRepository:

    def search(self, filters: SearchFilters):

        conditions = [
            "p.IsApproved = 1",
            "p.IsDeleted = 0",
            "r.IsDeleted = 0",
        ]

        params = {}

        # ── Location ─────────────────────────────
        if filters.city:

            conditions.append(
                "p.City = :city"
            )

            params["city"] = filters.city

        if filters.governorate:

            conditions.append(
                "p.Government = :gov"
            )

            params["gov"] = filters.governorate

        # ── Price ────────────────────────────────
        if filters.min_price:

            conditions.append(
                "r.Month_rent >= :min_price"
            )

            params["min_price"] = (
                filters.min_price
            )

        if filters.max_price:

            conditions.append(
                "r.Month_rent <= :max_price"
            )

            params["max_price"] = (
                filters.max_price
            )

        # ── Tenant type ──────────────────────────
        if filters.tenant_type == "student":

            conditions.append(
                "(at.AllowsStudents = 1)"
            )

        elif filters.tenant_type == "worker":

            conditions.append(
                "(at.AllowsWorkers = 1)"
            )

        # ── Shared / Private ─────────────────────
        if filters.shared_room is True:

            conditions.append(
                "r.Capacity > 1"
            )

        elif filters.shared_room is False:

            conditions.append(
                "r.Capacity = 1"
            )

        # ── Amenities ────────────────────────────
        if filters.wifi:

            conditions.append(
                "pa.Wifi = 1"
            )

        if filters.furnished:

            conditions.append(
                "r.Furnished = 1"
            )

        if filters.balcony:

            conditions.append(
                "r.Balcony = 1"
            )

        if filters.private_bathroom:

            conditions.append(
                "r.EnSuiteBathroom = 1"
            )

        # ── Sorting ──────────────────────────────
        order_clause = "r.CreatedAt DESC"

        if filters.sort_by == "price_low":

            order_clause = (
                "r.Month_rent ASC"
            )

        elif filters.sort_by == "price_high":

            order_clause = (
                "r.Month_rent DESC"
            )

        query = f"""
        SELECT TOP 5

            r.Id,
            r.RoomName,
            r.Month_rent,
            r.Deposit,

            r.Capacity,
            r.Furnished,
            r.Balcony,
            r.EnSuiteBathroom,

            p.Name AS PropertyName,
            p.City,
            p.Government,

            pa.Wifi

        FROM Rooms r

        JOIN Properties p
            ON r.PropertyId = p.Id

        LEFT JOIN AllowedTenants at
            ON at.RoomId = r.Id

        LEFT JOIN PropertyAmenities pa
            ON pa.PropertyId = p.Id

        WHERE {' AND '.join(conditions)}

        ORDER BY {order_clause}
        """

        with engine.connect() as conn:

            rows = conn.execute(
                text(query),
                params,
            ).mappings().all()

        return rows