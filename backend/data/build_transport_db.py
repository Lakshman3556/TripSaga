import os
import sys
import json
from typing import List

# Import Pydantic models for validated database seeding
from pydantic import BaseModel, Field

# Ensure root directory is added to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import DB helper functions
from app.core.db import init_db, get_db_connection

class DistanceSeederModel(BaseModel):
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    mode: str = Field(..., min_length=3)
    duration_hours: float = Field(..., gt=0.0)
    cost_inr: int = Field(..., ge=0)

class CityCostSeederModel(BaseModel):
    city: str = Field(..., min_length=1)
    hotel_budget_per_night: int = Field(..., ge=0)
    hotel_midrange_per_night: int = Field(..., ge=0)
    food_per_day_estimate: int = Field(..., ge=0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class TransportMatrixModel(BaseModel):
    distances: List[DistanceSeederModel]
    city_costs: List[CityCostSeederModel]

def populate_db() -> None:
    json_path = os.path.join(os.path.dirname(__file__), "transport_matrix.json")
    
    if not os.path.exists(json_path):
        print(f"Error: Could not find JSON source file at {json_path}")
        return

    print("Initializing SQLite database tables...")
    # Initialize the tables inside distances.db
    init_db()

    print("Reading and parsing JSON file...")
    with open(json_path, "r") as f:
        raw_json_data = json.load(f)

    print("Validating dataset structure using Pydantic...")
    try:
        validated_matrix = TransportMatrixModel.model_validate(raw_json_data)
    except Exception as err:
        print(f"Pydantic Validation failed! Please fix json structure. Error: {err}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Seed distances table
    print(f"Seeding {len(validated_matrix.distances)} distance routes...")
    for dist in validated_matrix.distances:
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO distances (origin, destination, mode, duration_hours, cost_inr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (dist.origin, dist.destination, dist.mode, dist.duration_hours, dist.cost_inr)
            )
        except Exception as e:
            print(f"Failed to insert distance record: {dist}. Error: {e}")

    # 2. Seed city_costs table with latitude/longitude coordinates
    print(f"Seeding {len(validated_matrix.city_costs)} city cost profiles with coordinate markers...")
    for cost in validated_matrix.city_costs:
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO city_costs (city, hotel_budget_per_night, hotel_midrange_per_night, food_per_day_estimate, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cost.city, cost.hotel_budget_per_night, cost.hotel_midrange_per_night, cost.food_per_day_estimate, cost.latitude, cost.longitude)
            )
        except Exception as e:
            print(f"Failed to insert cost record: {cost}. Error: {e}")

    conn.commit()
    conn.close()
    print("Database seeding completed successfully for all 69 cities with coordinates!")

if __name__ == "__main__":
    populate_db()
