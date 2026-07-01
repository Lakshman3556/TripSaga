from typing import TypedDict, Optional, List, Dict, Any

class TripState(TypedDict):
    """
    Shared state schema representing the data flowing through the LangGraph agents.
    
    Example state flow:
        1. Form inputs are initialized.
        2. Planner Agent fills 'task_plan'.
        3. Knowledge Retriever fills 'retrieved_places'.
        4. Transport+Budget fills 'transport_info' and 'budget_breakdown'.
        5. Itinerary Composer fills 'draft_itinerary'.
        6. Reviewer Agent checks constraints and saves 'final_itinerary'.
    """
    # --- Form Inputs ---
    origin: str
    destination: str
    days: int
    budget: Optional[int]
    transport_pref: str  # flight, train, bus, car
    interests: List[str]  # e.g. ["temples", "nature", "history"]
    
    # --- Agent Outputs (populated progressively) ---
    task_plan: Optional[Dict[str, Any]]          # Output of Agent 1 (Planner)
    retrieved_places: Optional[List[Dict[str, Any]]] # Output of Agent 2 (Retriever)
    transport_info: Optional[Dict[str, Any]]       # Output of Agent 3 (Transport)
    budget_breakdown: Optional[Dict[str, Any]]     # Output of Agent 3 (Budget)
    draft_itinerary: Optional[Dict[str, Any]]      # Output of Agent 4 (Composer)
    final_itinerary: Optional[Dict[str, Any]]      # Output of Agent 5 (Reviewer)
    
    # --- Graph Execution Status ---
    current_agent: str
    errors: List[str]
