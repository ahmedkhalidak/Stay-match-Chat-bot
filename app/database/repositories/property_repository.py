from sqlalchemy import text

from app.database.connection import engine
from app.models.search_models import SearchFilters


class PropertyRepository:

    def search(self, filters: SearchFilters):

        conditions = [
            "p.IsApproved = 1",
            "p.IsDeleted = 0",
            "p.PropertyType = 1",
        ]

        params = {}

        # ── Location ─────────────────────────────
        if filters.city:
            conditions.append("p.City = :city")
            params["city"] = filters.city

        if filters.governorate:
            conditions.append("p.Government = :gov")
            params["gov"] = filters.governorate

        # ── Price ────────────────────────────────
        if filters.min_price:
            conditions.append("p.MonthlyRent >= :min_price")
            params["min_price"] = filters.min_price

        if filters.max_price:
            conditions.append("p.MonthlyRent <= :max_price")
            params["max_price"] = filters.max_price

        # ── Sorting ─────────────────────────────
        order_clause = "p.CreatedAt DESC"

        if filters.sort_by == "price_low":
            order_clause = "p.MonthlyRent ASC"

        elif filters.sort_by == "price_high":
            order_clause = "p.MonthlyRent DESC"

        query = f"""
        SELECT TOP 5
            p.Id,
            p.Name,
            p.MonthlyRent,
            p.Deposite,

            p.City,
            p.Government

        FROM Properties p

        WHERE {' AND '.join(conditions)}

        ORDER BY {order_clause}
        """

        with engine.connect() as conn:
            rows = conn.execute(
                text(query),
                params,
            ).mappings().all()

        return rows