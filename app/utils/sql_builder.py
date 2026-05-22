"""
Shared SQL building utilities for repositories.
"""


def build_location_conditions(
    name: str,
    params: dict,
    prefix: str,
    table_alias: str = "p"
) -> list[str]:
    """
    Build comprehensive location conditions for SQL WHERE clauses.
    
    Supports:
    - City = name (case-insensitive)
    - Government = name (case-insensitive)
    - City LIKE name (partial match)
    - Government LIKE name (partial match)
    - If name is a known governorate → City IN (first 20 cities only to avoid parameter limit)
    
    Args:
        name: Location name (city or governorate)
        params: SQL parameters dict (will be modified in-place)
        prefix: Parameter prefix (e.g., "city" or "gov")
        table_alias: Table alias for the columns (default: "p")
    
    Returns:
        List of SQL condition strings
    """
    from app.utils.location_mapping import location_mapping
    
    conds = [
        f"LOWER({table_alias}.City) = LOWER(:{prefix}_name)",
        f"LOWER({table_alias}.Government) = LOWER(:{prefix}_name)",
        f"{table_alias}.City LIKE :{prefix}_name_like",
        f"{table_alias}.Government LIKE :{prefix}_name_like",
    ]
    params[f"{prefix}_name"] = name
    params[f"{prefix}_name_like"] = f"%{name}%"

    # If the name is a known governorate → add first 20 cities only
    # FreeTDS has a parameter limit
    cities = location_mapping.get_cities(name)
    if cities:
        # Limit to first 20 cities to avoid parameter limit
        cities = cities[:20]
        placeholders = []
        for i, city in enumerate(cities):
            key = f"{prefix}_c{i}"
            params[key] = city
            placeholders.append(f":{key}")
        conds.append(f"{table_alias}.City IN ({', '.join(placeholders)})")

    return conds
