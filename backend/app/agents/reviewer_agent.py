import json
from app.core.llm import get_llm
from app.agents.state import TripState

def run_reviewer_agent(state: TripState) -> TripState:
    """
    Agent 5 (Reviewer): LLM-based guardrail node.
    Validates the composed itinerary against day-count, budget limits, 
    and checks for logical inconsistencies (e.g. duplicate locations).
    """
    print(f"[{state['current_agent']}] Reviewing draft itinerary for constraints...")

    # Validate that we have a draft itinerary to review
    if not state.get("draft_itinerary"):
        state["errors"] = ["Reviewer failed: No draft itinerary found in state."]
        return state

    # Load LLM client in JSON mode
    llm = get_llm(temperature=0.1, json_mode=True)

    system_prompt = (
        "You are the Reviewer Agent for a South India Travel Planner.\n"
        "Your task is to inspect the draft itinerary and ensure it meets all travel constraints.\n\n"
        "INSPECTION CHECKLIST:\n"
        f"1. DAY COUNT: The itinerary MUST contain plans for exactly {state['days']} days. "
        f"If the draft contains more or fewer days, you must correct it to have exactly {state['days']} days "
        "('Day 1' through 'Day N').\n"
        f"2. BUDGET LIMIT: If the user provided a budget limit of {state.get('budget')} INR, check if the total "
        f"estimated cost of {state['budget_breakdown'].get('total_cost')} INR exceeds it. "
        "If it exceeds the budget, rewrite the descriptions to emphasize lower-cost alternatives (e.g., budget hotels, "
        "street food, free parks) and reduce the total cost estimation context.\n"
        "3. LOGIC CHECK: Ensure no specific attraction or restaurant is duplicated across multiple days.\n\n"
        "OUTPUT SCHEMA:\n"
        "Return a JSON object with two main fields:\n"
        "1. 'itinerary': The corrected day-wise plan matching the original composer JSON structure.\n"
        "2. 'review_notes': A list of strings explaining each issue you found and corrected. "
        "If no corrections were needed, leave this list empty: [].\n"
        "Respond ONLY in valid JSON matching this schema."
    )

    user_prompt = (
        f"Draft Itinerary:\n{json.dumps(state['draft_itinerary'])}\n\n"
        f"Requested Days: {state['days']}\n"
        f"Budget Limit: {state.get('budget')} INR\n"
        f"Calculated Budget Breakdown: {state['budget_breakdown']}"
    )

    try:
        messages = [
            ("system", system_prompt),
            ("user", user_prompt)
        ]
        response = llm.invoke(messages)
        parsed_review = json.loads(response.content)

        # Update final state outputs
        state["final_itinerary"] = parsed_review.get("itinerary")
        # Save review comments in the errors list as notes, or as a metadata field
        state["errors"] = parsed_review.get("review_notes", [])
    except Exception as e:
        print(f"Error in Reviewer Agent: {e}")
        state["errors"] = [f"Reviewer Agent failed: {str(e)}"]

    return state
