import json
from app.core.llm import get_llm
from app.agents.state import TripState

def run_planner_agent(state: TripState) -> TripState:
    """
    Agent 1 (Planner): Converts user profile into specific search queries for ChromaDB retrieval.
    """
    print(f"[{state['current_agent']}] Planning retrieval queries for {state['destination']}...")

    # Load LLM client in JSON mode
    llm = get_llm(temperature=0.4, json_mode=True)
    
    # System instruction
    system_prompt = (
        "You are the Planner Agent for a South India Travel Planner.\n"
        "Your task is to convert the user's travel profile into specific search queries for a vector database.\n"
        "Generate a JSON object with two keys:\n"
        "1. 'retrieval_queries': A list of 2-3 specific semantic search queries targeting attractions, hotels, or food "
        f"in the destination city: '{state['destination']}' based on the user's interests: {state['interests']}.\n"
        "2. 'priority_interests': A copy of the user's priority interests.\n"
        "Respond ONLY in valid JSON matching the format: "
        "{'retrieval_queries': ['query1', 'query2'], 'priority_interests': ['tag1', 'tag2']}"
    )
    
    user_prompt = (
        f"Destination: {state['destination']}\n"
        f"Interests: {state['interests']}\n"
        f"Days: {state['days']}"
    )
    
    try:
        # Query LLM
        messages = [
            ("system", system_prompt),
            ("user", user_prompt)
        ]
        response = llm.invoke(messages)
        parsed_plan = json.loads(response.content)
        
        # Update shared state
        state["task_plan"] = parsed_plan
        state["errors"] = []
    except Exception as e:
        print(f"Error in Planner Agent: {e}")
        state["errors"] = [f"Planner Agent failed: {str(e)}"]
        
    return state
