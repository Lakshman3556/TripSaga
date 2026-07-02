from app.core.vectorstore import query_places
from app.agents.state import TripState
from typing import List, Dict, Any

def run_knowledge_retriever(state: TripState) -> TripState:
    """
    Agent 2 (Retriever): Queries ChromaDB for attractions (in destination and nearby cities if days >= 4),
    and retrieves real hotels and restaurants from the destination city.
    """
    print(f"[{state['current_agent']}] Querying ChromaDB for places in {state['destination']}...")

    # Validate that we have a task plan to work with
    if not state.get("task_plan") or "retrieval_queries" not in state["task_plan"]:
        state["errors"] = ["Retriever failed: No task plan with retrieval queries found."]
        return state

    queries = state["task_plan"]["retrieval_queries"]
    city = state["destination"]
    days = state["days"]

    # 1. Detect nearby cities if days >= 4
    from app.core.db import get_db_connection, calculate_haversine_distance
    
    nearby_cities = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT city, latitude, longitude FROM city_costs")
        city_rows = cursor.fetchall()
        conn.close()
        
        # Get coordinates of main destination city
        dest_lat, dest_lon = None, None
        for row in city_rows:
            if row["city"].lower() == city.lower():
                dest_lat = row["latitude"]
                dest_lon = row["longitude"]
                break
                
        if dest_lat is not None and dest_lon is not None and days >= 4:
            distances = []
            for row in city_rows:
                other_city = row["city"]
                if other_city.lower() == city.lower():
                    continue
                dist = calculate_haversine_distance(dest_lat, dest_lon, row["latitude"], row["longitude"])
                distances.append((other_city, dist))
            
            # Sort by distance and pick top 2 within 150km
            distances.sort(key=lambda x: x[1])
            for other_city, dist in distances[:2]:
                if dist <= 150.0:
                    nearby_cities.append(other_city)
                    
            print(f"[{state['current_agent']}] Multi-city planning enabled! Nearest cities: {nearby_cities}")
    except Exception as db_err:
        print(f"Failed to calculate nearby cities: {db_err}")

    seen_ids = set()
    unique_places: List[Dict[str, Any]] = []

    # Helper to add results to the list
    def add_unique_results(results):
        for item in results:
            place_id = item["id"]
            if place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_places.append({
                    "id": place_id,
                    "name": item["metadata"]["name"],
                    "city": item["metadata"].get("city", city), # Track the city name
                    "category": item["metadata"]["category"],
                    "description": item["document"],
                    "rating": item["metadata"]["rating"],
                    "interest_tags": item["metadata"].get("interest_tags", [])
                })

    # 2. Query Attractions (Main City + Nearby Cities if enabled)
    for query in queries:
        try:
            # Attractions in main city
            results = query_places(query_text=query, city=city, category="attraction", n_results=4)
            add_unique_results(results)
            
            # Attractions in nearby cities
            for near_city in nearby_cities:
                near_results = query_places(query_text=query, city=near_city, category="attraction", n_results=3)
                add_unique_results(near_results)
        except Exception as e:
            print(f"Failed query search for query: '{query}'. Error: {e}")

    # 3. Explicitly Query Hotels in Main City
    try:
        hotel_results = query_places(
            query_text="hotels stay luxury midrange budget lodging accommodation",
            city=city,
            category="hotel",
            n_results=5
        )
        add_unique_results(hotel_results)
    except Exception as e:
        print(f"Failed hotel search. Error: {e}")

    # 4. Explicitly Query Restaurants in Main City
    try:
        restaurant_results = query_places(
            query_text="restaurants local food delicious lunch dinner breakfast dining eats",
            city=city,
            category="restaurant",
            n_results=6
        )
        add_unique_results(restaurant_results)
    except Exception as e:
        print(f"Failed restaurant search. Error: {e}")

    state["retrieved_places"] = unique_places
    print(f"[{state['current_agent']}] Retrieved {len(unique_places)} unique places (attractions, hotels, and restaurants) for {city} and surrounding cities.")
    
    # If ChromaDB returned empty results, log an error state
    if not unique_places:
        state["errors"] = [f"No places retrieved in ChromaDB for '{city}'."]
        
    return state
