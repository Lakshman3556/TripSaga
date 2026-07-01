from app.core.db import get_route_details
from app.agents.state import TripState

def run_transport_budget_agent(state: TripState) -> TripState:
    """
    Agent 3 (Transport + Budget): Pure deterministic code.
    Queries the SQLite distance table for transit details, and calculates 
    a realistic budget estimate based on standard city cost sheets.
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

    # Extract transport metrics
    transport_info = {
        "mode": route["mode"],
        "duration_hours": route["duration_hours"],
        "cost_inr": route["cost_inr"],
        "route_type": route["type"]
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
