import json
from app.core.llm import get_llm
from app.agents.state import TripState

def run_itinerary_composer_agent(state: TripState) -> TripState:
    """
    Agent 4 (Composer): LLM-based node.
    Synthesizes the retrieved places and transport/budget metadata into 
    a structured, day-wise travel itinerary matching the target day count.
    """
    print(f"[{state['current_agent']}] Composing draft itinerary for {state['destination']}...")

    # Load LLM client in JSON mode
    llm = get_llm(temperature=0.3, json_mode=True)

    # Format the retrieved places data into a neat text block for the LLM
    places_formatted = []
    for idx, p in enumerate(state["retrieved_places"] or []):
        places_formatted.append(
            f"[{idx+1}] Name: {p['name']} | Category: {p['category']} | Rating: {p['rating']} "
            f"| Tags: {p['interest_tags']} | Description: {p['description']}"
        )
    places_text = "\n".join(places_formatted)

    # System instruction
    system_prompt = (
        "You are the Itinerary Composer Agent for a South India Travel Planner.\n"
        "Your task is to organize raw place data, hotels, and restaurants into a day-by-day travel plan.\n\n"
        "CRITICAL RULES:\n"
        f"1. You MUST generate plan details for EXACTLY {state['days']} days. The JSON keys must be "
        "exactly 'Day 1', 'Day 2', ..., matching the day count.\n"
        "2. Do NOT invent or make up any attraction, hotel, or restaurant name that is not present in "
        "the provided list. Use ONLY the names and descriptions provided.\n"
        "3. Provide realistic recommendations. Recommend a hotel stay, logical sights for morning/afternoon/evening, "
        "and specify breakfast, lunch, and dinner recommendations in the 'meals' dict using the provided restaurants.\n"
        "4. Respond ONLY in valid JSON matching this schema:\n"
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
        f"Budget Breakdown context: {state['budget_breakdown']}\n"
        f"Retrieved Places to Choose From:\n{places_text}"
    )

    try:
        messages = [
            ("system", system_prompt),
            ("user", user_prompt)
        ]
        response = llm.invoke(messages)
        parsed_itinerary = json.loads(response.content)

        # Save output in draft_itinerary
        state["draft_itinerary"] = parsed_itinerary
        state["errors"] = []
    except Exception as e:
        print(f"Error in Itinerary Composer Agent: {e}")
        state["errors"] = [f"Composer Agent failed: {str(e)}"]

    return state
