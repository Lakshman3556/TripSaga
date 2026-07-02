import json
from app.core.llm import get_llm, clean_json_response
from app.agents.state import TripState

def run_itinerary_composer_agent(state: TripState) -> TripState:
    """
    Agent 4 (Composer): LLM-based node.
    Synthesizes the retrieved places and transport/budget metadata into 
    a structured, day-wise travel itinerary matching the target day count.
    Uses real hotels, real restaurants, and formats multi-city days.
    """
    print(f"[{state['current_agent']}] Composing draft itinerary for {state['destination']}...")

    # Load LLM client in JSON mode
    llm = get_llm(temperature=0.3, json_mode=True)

    # Separate retrieved places into categories for the LLM
    places = state["retrieved_places"] or []
    attractions = [p for p in places if p["category"] == "attraction"]
    hotels = [p for p in places if p["category"] == "hotel"]
    restaurants = [p for p in places if p["category"] == "restaurant"]

    # Format Attractions list (includes which city it belongs to)
    attractions_text = "\n".join([
        f"- {p['name']} (City: {p['city']}) | Rating: {p['rating']} | Tags: {p['interest_tags']} | Description: {p['description']}"
        for p in attractions
    ])

    # Format Hotels list
    hotels_text = "\n".join([
        f"- {p['name']} (City: {p['city']}) | Rating: {p['rating']} | Description: {p['description']}"
        for p in hotels
    ])

    # Format Restaurants list
    restaurants_text = "\n".join([
        f"- {p['name']} (City: {p['city']}) | Rating: {p['rating']} | Tags: {p['interest_tags']} | Description: {p['description']}"
        for p in restaurants
    ])

    # System instruction
    system_prompt = (
        "You are the Itinerary Composer Agent for a South India Travel Planner.\n"
        "Your task is to organize raw place data, hotels, and restaurants into a day-by-day travel plan.\n\n"
        "CRITICAL RULES:\n"
        f"1. You MUST generate plan details for EXACTLY {state['days']} days. The JSON keys must be "
        "exactly 'Day 1', 'Day 2', ..., matching the day count.\n"
        "2. Do NOT invent or make up any attraction, hotel, or restaurant name. Use ONLY the names and descriptions provided.\n"
        "3. HOTELS: For accommodation recommendations, recommend ONLY the hotels from the provided 'AVAILABLE HOTELS' list. "
        "Mention the hotel name explicitly in the morning details or daily notes.\n"
        "4. RESTAURANTS & MEALS: In the 'meals' dict for each day, you must suggest real restaurants from the "
        "'AVAILABLE RESTAURANTS' list. Assign a specific restaurant name and recommended food for breakfast, lunch, and dinner. "
        "Do not use generic descriptions like 'local eatery'—mention the restaurant name (e.g. 'Chutneys' or 'Bawarchi').\n"
        "5. MULTI-CITY LOGIC: If there are attractions in the 'AVAILABLE ATTRACTIONS' list from cities other than the main "
        f"destination city: '{state['destination']}', distribute the days dynamically. For example, spend Day 1 and 2 in the "
        "main destination city, and Day 3 and 4 in the neighboring city (e.g., Kodaikanal or Rameshwaram). Clearly state in the "
        "description which city the traveler is exploring that day.\n"
        "6. TRANSPORT WARNING: If a transport warning is provided in the user prompt (e.g., travel takes a very long time), "
        "design Day 1 morning or afternoon to account for the travel/transit phase, and add notes encouraging the user "
        "to consider the recommended alternative (like a flight or train).\n\n"
        "Respond ONLY in valid JSON matching this schema:\n"
        "{\n"
        "  'Day 1': {\n"
        "    'morning': 'description',\n"
        "    'afternoon': 'description',\n"
        "    'evening': 'description',\n"
        "    'meals': {\n"
        "      'breakfast': 'description',\n"
        "      'lunch': 'description',\n"
        "      'dinner': 'description'\n"
        "    }\n"
        "  }\n"
        "}"
    )

    user_prompt = (
        f"Destination City: {state['destination']}\n"
        f"Trip Length: {state['days']} Days\n"
        f"Preferred Transport Mode: {state['transport_info'].get('mode')}\n"
        f"Travel Cost & Duration: {state['transport_info'].get('cost_inr')} INR one-way, {state['transport_info'].get('duration_hours')} hours\n"
        f"Transport Warning/Recommendation: {state['transport_info'].get('warning') or 'None'}\n"
        f"Budget Breakdown context: {state['budget_breakdown']}\n\n"
        f"--- AVAILABLE HOTELS (Select stays from here) ---\n{hotels_text or 'None'}\n\n"
        f"--- AVAILABLE RESTAURANTS (Select meals from here) ---\n{restaurants_text or 'None'}\n\n"
        f"--- AVAILABLE ATTRACTIONS (Plan visits from here) ---\n{attractions_text}"
    )

    try:
        messages = [
            ("system", system_prompt),
            ("user", user_prompt)
        ]
        response = llm.invoke(messages)
        cleaned_content = clean_json_response(response.content)
        parsed_itinerary = json.loads(cleaned_content)

        # Save output in draft_itinerary
        state["draft_itinerary"] = parsed_itinerary
        state["errors"] = []
    except Exception as e:
        print(f"Error in Itinerary Composer Agent: {e}")
        state["errors"] = [f"Composer Agent failed: {str(e)}"]

    return state
