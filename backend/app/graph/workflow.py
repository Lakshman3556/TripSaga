from langgraph.graph import StateGraph, END
from app.agents.state import TripState
from app.agents.planner_agent import run_planner_agent
from app.agents.knowledge_retriever import run_knowledge_retriever
from app.agents.transport_budget import run_transport_budget_agent
from app.agents.itinerary_composer import run_itinerary_composer_agent
from app.agents.reviewer_agent import run_reviewer_agent
from typing import Dict, Any

# Define node wrapper functions that update the current active agent metadata 
# before executing the respective agent logic.
def planner_node(state: TripState) -> TripState:
    state["current_agent"] = "Planner Agent"
    return run_planner_agent(state)

def retriever_node(state: TripState) -> TripState:
    state["current_agent"] = "Knowledge Retriever"
    return run_knowledge_retriever(state)

def transport_budget_node(state: TripState) -> TripState:
    state["current_agent"] = "Transport + Budget Agent"
    return run_transport_budget_agent(state)

def composer_node(state: TripState) -> TripState:
    state["current_agent"] = "Itinerary Composer"
    return run_itinerary_composer_agent(state)

def reviewer_node(state: TripState) -> TripState:
    state["current_agent"] = "Reviewer Agent"
    return run_reviewer_agent(state)

# 1. Initialize State Graph
workflow = StateGraph(TripState)

# 2. Add Nodes to Graph
workflow.add_node("planner", planner_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("transport_budget", transport_budget_node)
workflow.add_node("composer", composer_node)
workflow.add_node("reviewer", reviewer_node)

# 3. Connect nodes with Edges (sequential pipeline)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "retriever")
workflow.add_edge("retriever", "transport_budget")
workflow.add_edge("transport_budget", "composer")
workflow.add_edge("composer", "reviewer")
workflow.add_edge("reviewer", END)

# 4. Compile the Graph
app_graph = workflow.compile()

def generate_itinerary(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main client entrypoint to trigger the compiled multi-agent LangGraph workflow.
    """
    # Initialize the starting state
    initial_state: TripState = {
        "origin": inputs["origin"],
        "destination": inputs["destination"],
        "days": inputs["days"],
        "budget": inputs.get("budget"),
        "transport_pref": inputs["transport_pref"],
        "interests": inputs.get("interests", []),
        "task_plan": None,
        "retrieved_places": None,
        "transport_info": None,
        "budget_breakdown": None,
        "draft_itinerary": None,
        "final_itinerary": None,
        "current_agent": "Initialization",
        "errors": []
    }
    
    # Run the graph synchronously
    final_state = app_graph.invoke(initial_state)
    return final_state
