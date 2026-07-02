from app.core.db import get_route_details
from app.agents.state import TripState

# Airport Mapping for South India cities
AIRPORT_MAP = {
    "hyderabad": "Rajiv Gandhi International Airport (HYD)",
    "bengaluru": "Kempegowda International Airport (BLR)",
    "chennai": "Chennai International Airport (MAA)",
    "kochi": "Cochin International Airport (COK)",
    "coimbatore": "Coimbatore International Airport (CJB)",
    "madurai": "Madurai Airport (IXM)",
    "tirupati": "Tirupati Airport (TIR)",
    "visakhapatnam": "Visakhapatnam International Airport (VTZ)",
    "vijayawada": "Vijayawada Airport (VGA)",
    "mangalore": "Mangaluru International Airport (IXE)",
    "thiruvananthapuram": "Trivandrum International Airport (TRV)",
    "kovalam": "Trivandrum International Airport (TRV) (approx. 15 km away)",
    "kozhikode": "Calicut International Airport (CCJ)",
    "pondicherry": "Pondicherry Airport (PNY)",
    "trichy": "Tiruchirappalli International Airport (TRZ)",
    "tanjore": "Tiruchirappalli International Airport (TRZ) (approx. 60 km away)",
    "ooty": "Coimbatore Airport (CJB) (approx. 90 km away)",
    "munnar": "Cochin International Airport (COK) (approx. 110 km away)",
    "coorg": "Mangaluru Airport (IXE) (approx. 140 km away) or Kempegowda Airport (BLR)",
    "hampi": "Jindal Vijayanagar Airport (VDY) or Hubli Airport (HBX)",
    "gokarna": "Dabolim Airport Goa (GOI) (approx. 140 km away)",
    "alleppey": "Cochin International Airport (COK) (approx. 80 km away)",
    "wayanad": "Calicut International Airport (CCJ) (approx. 90 km away)",
    "araku valley": "Visakhapatnam Airport (VTZ) (approx. 115 km away)",
    "warangal": "Rajiv Gandhi International Airport (HYD) (approx. 170 km away)",
    "yadadri": "Rajiv Gandhi International Airport (HYD) (approx. 90 km away)",
}

def get_nearest_airport(city_name: str) -> str:
    """Helper to fetch nearest commercial airport name."""
    return AIRPORT_MAP.get(city_name.lower(), f"{city_name} Domestic/International Airport")

def run_transport_budget_agent(state: TripState) -> TripState:
    """
    Agent 3 (Transport + Budget): Pure deterministic code.
    Queries the SQLite distance table for transit details, and calculates 
    a realistic budget estimate based on standard city cost sheets.
    Also flags long travel times and recommends airport terminals when applicable.
    """
    origin = state["origin"]
    dest = state["destination"]
    pref_mode = state["transport_pref"]
    days = state["days"]
    user_budget = state.get("budget")

    print(f"[{state['current_agent']}] Checking transport and budget from {origin} to {dest}...")

    # Fetch routing details from SQLite
    route = get_route_details(origin, dest, pref_mode)

    if not route:
        state["errors"] = [f"Could not find any routing route between '{origin}' and '{dest}' in SQLite database."]
        return state

    # Check if trip is long-duration (driving/bus takes >= 8 hours)
    duration_hours = route["duration_hours"]
    warning_msg = None
    if pref_mode in ["car", "bus"] and duration_hours >= 8.0:
        warning_msg = (
            f"Driving distance from {origin} to {dest} is quite long "
            f"({duration_hours} hours). We recommend taking a flight "
            f"from {get_nearest_airport(origin)} to {get_nearest_airport(dest)} "
            f"or taking a train to save travel time."
        )

    # Extract transport metrics
    transport_info = {
        "mode": route["mode"],
        "duration_hours": duration_hours,
        "cost_inr": route["cost_inr"],
        "route_type": route["type"],
        "origin_airport": get_nearest_airport(origin),
        "destination_airport": get_nearest_airport(dest),
        "warning": warning_msg
    }

    # Calculate accommodation cost estimates
    # If the user has a tight budget limit, choose budget hotel rates. Else midrange.
    if user_budget and user_budget <= 8000:
        hotel_rate = route["hotel_budget_per_night"]
    else:
        hotel_rate = route["hotel_midrange_per_night"]

    hotel_total = hotel_rate * max(1, (days - 1))  # nights = days - 1
    food_total = route["food_per_day_estimate"] * days
    
    # Transport costs (two-way trip)
    transport_total = route["cost_inr"] * 2

    # Calculate overall estimate
    total_estimate = hotel_total + food_total + transport_total

    # Update state fields
    state["transport_info"] = transport_info
    state["budget_breakdown"] = {
        "transport_cost": transport_total,
        "hotel_cost": hotel_total,
        "food_cost": food_total,
        "total_cost": total_estimate
    }

    print(f"[{state['current_agent']}] Transport cost: INR {transport_total}, Hotel total: INR {hotel_total}, Food total: INR {food_total}. Total Estimate: INR {total_estimate}.")
    return state
