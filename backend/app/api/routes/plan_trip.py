from fastapi import APIRouter, HTTPException, status
from app.models.request import TripRequest
from app.models.response import TripResponse, DayPlan, BudgetDetail, RouteDetail
from app.core.guardrails import validate_cities
from app.graph.workflow import generate_itinerary

router = APIRouter()

@router.post("/plan", response_model=TripResponse)
def plan_trip_endpoint(payload: TripRequest):
    """
    HTTP POST Endpoint to trigger the LangGraph travel planner workflow.
    """
    # 1. Execute Guardrail Checks
    is_valid, err_msg = validate_cities(payload.origin, payload.destination)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )
        
    # 2. Trigger the LangGraph Workflow
    print(f"\n--- Starting Agent Workflow for {payload.origin} -> {payload.destination} ({payload.days} days) ---")
    inputs = {
        "origin": payload.origin,
        "destination": payload.destination,
        "days": payload.days,
        "budget": payload.budget,
        "transport_pref": payload.transport_pref,
        "interests": payload.interests
    }
    
    result = generate_itinerary(inputs)
    
    # 3. Handle Workflow Errors
    if result.get("errors") and any("failed" in err.lower() for err in result["errors"]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow failed: {', '.join(result['errors'])}"
        )
        
    # 4. Package and serialize state results into the strict Pydantic Response Model
    try:
        route_detail = RouteDetail(
            mode=result["transport_info"]["mode"],
            duration_hours=result["transport_info"]["duration_hours"],
            cost_inr=result["transport_info"]["cost_inr"],
            route_type=result["transport_info"]["route_type"]
        )
        
        budget_detail = BudgetDetail(
            transport_cost=result["budget_breakdown"]["transport_cost"],
            hotel_cost=result["budget_breakdown"]["hotel_cost"],
            food_cost=result["budget_breakdown"]["food_cost"],
            total_cost=result["budget_breakdown"]["total_cost"]
        )
        
        # Parse day-wise itinerary dict items into DayPlan models
        itinerary_data = {}
        for day, plan in result["final_itinerary"].items():
            itinerary_data[day] = DayPlan(
                morning=plan["morning"],
                afternoon=plan["afternoon"],
                evening=plan["evening"],
                meals=plan["meals"]
            )
            
        response = TripResponse(
            origin=result["origin"],
            destination=result["destination"],
            days=result["days"],
            budget_limit=result.get("budget"),
            route=route_detail,
            budget_breakdown=budget_detail,
            itinerary=itinerary_data,
            review_notes=result.get("errors", [])  # reviewer notes are stored in the state's errors list
        )
        return response
    except Exception as parse_error:
        print(f"Serialization failed: {parse_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serialize final agent output: {str(parse_error)}"
        )
