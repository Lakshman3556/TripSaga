import os
import sqlite3
import math
import httpx # Used to query the free OSRM API
from typing import Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "distances.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """
    Initializes the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Distances Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distances (
            origin TEXT,
            destination TEXT,
            mode TEXT,
            duration_hours REAL,
            cost_inr INTEGER,
            PRIMARY KEY (origin, destination, mode)
        )
    """)
    
    # 2. City Costs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS city_costs (
            city TEXT PRIMARY KEY,
            hotel_budget_per_night INTEGER,
            hotel_midrange_per_night INTEGER,
            food_per_day_estimate INTEGER,
            latitude REAL,
            longitude REAL
        )
    """)
    
    conn.commit()
    conn.close()

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Mathematical fallback: great-circle distance between two points in km.
    """
    R = 6371.0 # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_heuristic_route(origin: str, destination: str, mode: str) -> Optional[Dict[str, Any]]:
    """
    Calculates road routing. Checks OSRM API for real road connectivity first.
    Falls back to straight-line distance if API is offline/unavailable.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT latitude, longitude FROM city_costs WHERE LOWER(city) = ?", (origin.lower(),))
    orig_row = cursor.fetchone()
    
    cursor.execute("SELECT latitude, longitude FROM city_costs WHERE LOWER(city) = ?", (destination.lower(),))
    dest_row = cursor.fetchone()
    
    conn.close()
    
    if not orig_row or not dest_row:
        return None
        
    lon1, lat1 = orig_row["longitude"], orig_row["latitude"]
    lon2, lat2 = dest_row["longitude"], dest_row["latitude"]
    
    distance_km = 0.0
    duration_hours = 0.0
    mode_lower = mode.lower()
    
    # 1. Try querying OpenStreetMap OSRM API for real roads
    try:
        # OSRM expects format: longitude,latitude;longitude,latitude
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        response = httpx.get(url, timeout=3.0)
        
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("code") == "Ok" and len(res_data.get("routes", [])) > 0:
                route = res_data["routes"][0]
                distance_km = route["distance"] / 1000.0 # Convert meters to km
                duration_hours = round(route["duration"] / 3600.0, 1) # Convert seconds to hours
                route_type = "osrm-road-api"
            else:
                raise ValueError("OSRM returned invalid route status")
        else:
            raise httpx.HTTPStatusError("OSRM API down", request=response.request, response=response)
            
    except Exception:
        # 2. Fallback to Haversine straight-line distance if internet/OSRM fails
        distance_km = calculate_haversine_distance(lat1, lon1, lat2, lon2)
        # Apply average speed logic
        speed_kmh = 50.0 if mode_lower == "car" else 45.0
        duration_hours = round((distance_km / speed_kmh) + 0.5, 1)
        route_type = "heuristic-haversine"

    # Define cost metrics per mode
    if mode_lower == "flight":
        cost_per_km = 8.0
        base_fee = 2000
    elif mode_lower == "train":
        cost_per_km = 1.2
        base_fee = 100
    elif mode_lower == "bus":
        cost_per_km = 2.0
        base_fee = 50
    else: # car
        cost_per_km = 12.0
        base_fee = 500
        
    cost_inr = int((distance_km * cost_per_km) + base_fee)
    
    return {
        "mode": mode,
        "duration_hours": duration_hours,
        "cost_inr": cost_inr,
        "type": route_type
    }
def get_route_details(origin: str, destination: str, mode: str) -> Optional[Dict[str, Any]]:
    """
    Routing engine that checks Direct -> Mode-based Fallbacks (Heuristic for road, Hubs for transit).
    
    Inputs:
        origin (str): e.g. "Warangal"
        destination (str): e.g. "Yadadri"
        mode (str): e.g. "car"
        
    Outputs:
        A dictionary containing duration_hours, cost_inr, and local destination costs.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- Tier 1: Direct Route Check ---
    cursor.execute(
        "SELECT duration_hours, cost_inr FROM distances WHERE LOWER(origin) = ? AND LOWER(destination) = ? AND LOWER(mode) = ?",
        (origin.lower(), destination.lower(), mode.lower())
    )
    direct_row = cursor.fetchone()
    
    # Fetch destination local costs
    cursor.execute(
        "SELECT hotel_budget_per_night, hotel_midrange_per_night, food_per_day_estimate FROM city_costs WHERE LOWER(city) = ?",
        (destination.lower(),)
    )
    cost_row = cursor.fetchone()
    
    if not cost_row:
        conn.close()
        return None
        
    cost_data = {
        "hotel_budget_per_night": cost_row["hotel_budget_per_night"],
        "hotel_midrange_per_night": cost_row["hotel_midrange_per_night"],
        "food_per_day_estimate": cost_row["food_per_day_estimate"]
    }
    
    # If a direct route is saved, return it immediately (for all modes)
    if direct_row:
        conn.close()
        return {
            "mode": mode,
            "duration_hours": direct_row["duration_hours"],
            "cost_inr": direct_row["cost_inr"],
            "type": "direct",
            **cost_data
        }
        
    # --- Mode-Based Routing Logic ---
    mode_lower = mode.lower()
    
    # A. If it's a road route (Car/Bus), skip Hubs and calculate a direct road route using coordinates (Heuristic with OSRM check)
    if mode_lower in ["car", "bus"]:
        conn.close()
        heuristic = get_heuristic_route(origin, destination, mode)
        if heuristic:
            return {
                **heuristic,
                **cost_data
            }
        return None
        
    # B. If it's public transit (Train/Flight), try Hub-and-Spoke routing first.
    hubs = ["hyderabad", "bengaluru", "chennai", "kochi", "visakhapatnam"]
    for hub in hubs:
        cursor.execute(
            "SELECT duration_hours, cost_inr FROM distances WHERE LOWER(origin) = ? AND LOWER(destination) = ? AND LOWER(mode) = ?",
            (origin.lower(), hub, mode_lower)
        )
        leg1 = cursor.fetchone()
        
        cursor.execute(
            "SELECT duration_hours, cost_inr FROM distances WHERE LOWER(origin) = ? AND LOWER(destination) = ? AND LOWER(mode) = ?",
            (hub, destination.lower(), mode_lower)
        )
        leg2 = cursor.fetchone()
        
        if leg1 and leg2:
            conn.close()
            return {
                "mode": mode,
                "duration_hours": round(leg1["duration_hours"] + leg2["duration_hours"], 1),
                "cost_inr": leg1["cost_inr"] + leg2["cost_inr"],
                "type": f"hub-fallback-via-{hub}",
                **cost_data
            }
            
    conn.close()
    
    # C. Absolute Fallback: if everything else fails, estimate with Heuristic.
    heuristic = get_heuristic_route(origin, destination, mode)
    if heuristic:
        return {
            **heuristic,
            **cost_data
        }
        
    return None
