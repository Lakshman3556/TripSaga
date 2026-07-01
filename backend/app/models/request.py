from pydantic import BaseModel, Field
from typing import List, Optional

class TripRequest(BaseModel):
    origin: str = Field(..., description="Starting city, e.g., 'Hyderabad'")
    destination: str = Field(..., description="Destination city, e.g., 'Madurai'")
    days: int = Field(..., ge=1, le=10, description="Number of days (1 to 10)")
    budget: Optional[int] = Field(None, ge=0, description="Optional total budget limit in INR")
    transport_pref: str = Field(..., description="Preferred travel mode: 'flight', 'train', 'bus', or 'car'")
    interests: List[str] = Field(default_factory=list, description="List of user interest tags, e.g., ['temples', 'history']")
