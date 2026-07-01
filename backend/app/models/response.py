from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DayPlan(BaseModel):
    morning: str = Field(..., description="Morning activity description")
    afternoon: str = Field(..., description="Afternoon activity description")
    evening: str = Field(..., description="Evening activity description")
    meals: Dict[str, str] = Field(..., description="Meal locations/recommendations, e.g., {'breakfast': '...', 'lunch': '...', 'dinner': '...'}")

class BudgetDetail(BaseModel):
    transport_cost: int = Field(..., description="Estimated cost of transportation in INR")
    hotel_cost: int = Field(..., description="Estimated cost of accommodation in INR")
    food_cost: int = Field(..., description="Estimated food expenses in INR")
    total_cost: int = Field(..., description="Total estimated trip cost in INR")

class RouteDetail(BaseModel):
    mode: str = Field(..., description="Selected transport mode")
    duration_hours: float = Field(..., description="One-way travel duration in hours")
    cost_inr: int = Field(..., description="One-way transport cost in INR")
    route_type: str = Field(..., description="Source of routing logic (direct / fallback)")

class TripResponse(BaseModel):
    origin: str
    destination: str
    days: int
    budget_limit: Optional[int]
    route: RouteDetail
    budget_breakdown: BudgetDetail
    itinerary: Dict[str, DayPlan] = Field(..., description="Keys should be 'Day 1', 'Day 2', etc.")
    review_notes: List[str] = Field(default_factory=list, description="Any adjustments made by the Reviewer Agent")
