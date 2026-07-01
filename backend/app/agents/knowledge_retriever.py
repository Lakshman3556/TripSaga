from app.core.vectorstore import query_places
from app.agents.state import TripState
from typing import List, Dict, Any

def run_knowledge_retriever(state: TripState) -> TripState:
    """
    Agent 2 (Retriever): Queries ChromaDB using the semantic search queries 
    from the Planner, filtered strictly by the destination city.
    """
    print(f"[{state['current_agent']}] Querying ChromaDB for places in {state['destination']}...")

    # Validate that we have a task plan to work with
    if not state.get("task_plan") or "retrieval_queries" not in state["task_plan"]:
        state["errors"] = ["Retriever failed: No task plan with retrieval queries found."]
        return state

    queries = state["task_plan"]["retrieval_queries"]
    city = state["destination"]

    seen_ids = set()
    unique_places: List[Dict[str, Any]] = []

    # Run query for each search string
    for query in queries:
        try:
            # Query top-5 places per search query, strictly matching the destination city
            results = query_places(query_text=query, city=city, n_results=5)
            
            for item in results:
                place_id = item["id"]
                if place_id not in seen_ids:
                    seen_ids.add(place_id)
                    unique_places.append({
                        "id": place_id,
                        "name": item["metadata"]["name"],
                        "category": item["metadata"]["category"],
                        "description": item["document"],
                        "rating": item["metadata"]["rating"],
                        "interest_tags": item["metadata"].get("interest_tags", [])
                    })
        except Exception as e:
            print(f"Failed query search: '{query}'. Error: {e}")

    state["retrieved_places"] = unique_places
    print(f"[{state['current_agent']}] Retrieved {len(unique_places)} unique places for {city}.")
    
    # If ChromaDB returned empty results, log an error state
    if not unique_places:
        state["errors"] = [f"No places retrieved in ChromaDB for '{city}'."]
        
    return state
