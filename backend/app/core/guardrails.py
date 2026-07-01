from app.core.db import get_db_connection
from typing import List, Tuple

def get_supported_cities() -> List[str]:
    """
    Fetches the list of all supported cities from the SQLite database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT city FROM city_costs ORDER BY city ASC")
    cities = [row["city"] for row in cursor.fetchall()]
    conn.close()
    return cities

def validate_cities(origin: str, destination: str) -> Tuple[bool, str]:
    """
    Validates if both origin and destination cities are supported.
    Returns (is_valid, error_message).
    """
    supported = {c.lower() for c in get_supported_cities()}
    
    if origin.lower() not in supported:
        return False, f"Origin city '{origin}' is not supported. We only support cities in South India."
    if destination.lower() not in supported:
        return False, f"Destination city '{destination}' is not supported. We only support cities in South India."
        
    return True, ""
