import os
import sys
import json
import httpx
from typing import List, Dict, Any

# Ensure root directory is added to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Vector Store client and SQLite DB helper
from app.core.vectorstore import add_places
from app.core.db import get_db_connection

def fetch_wikipedia_summary(city: str) -> str:
    """
    Helper to fetch a summary of a city from the free Wikipedia API.
    Used as an automated fallback if no local seed data is written.
    """
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city}"
        headers = {"User-Agent": "TripSageAI/1.0 (laksh@example.com)"}
        response = httpx.get(url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return data.get("extract", "")
    except Exception as e:
        print(f"Failed to fetch Wikipedia summary for {city}: {e}")
    return ""

def run_ingestion() -> None:
    """
    Main runner script to import place documents into ChromaDB.
    """
    print("Reading cities list from SQLite database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all cities seeded in SQLite
    cursor.execute("SELECT city FROM city_costs")
    cities = [row["city"] for row in cursor.fetchall()]
    conn.close()

    print(f"Found {len(cities)} cities to index.")

    # Load local seed places JSON
    seed_path = os.path.join(os.path.dirname(__file__), "seed_places.json")
    local_seed_data = {}
    if os.path.exists(seed_path):
        with open(seed_path, "r") as f:
            local_seed_data = json.load(f)
            print(f"Loaded high-quality seed profiles for {len(local_seed_data.keys())} cities.")

    payloads_to_embed = []

    for city in cities:
        print(f"Processing city: {city}...")
        
        # 1. Check if we have high-quality pre-scraped data
        if city in local_seed_data:
            place_list = local_seed_data[city]
            for idx, p in enumerate(place_list):
                payloads_to_embed.append({
                    "id": f"place_{city.lower()}_{p['category']}_{idx}",
                    "document": f"{p['name']} in {city}: {p['description']}",
                    "metadata": {
                        "name": p["name"],
                        "city": city,
                        "category": p["category"],
                        "rating": p["rating"],
                        "interest_tags": p["interest_tags"]
                    }
                })
        else:
            # 2. Dynamic Fallback: Fetch real overview data from Wikipedia API
            wiki_summary = fetch_wikipedia_summary(city)
            if wiki_summary:
                # Add city overview as a general attraction
                payloads_to_embed.append({
                    "id": f"place_{city.lower()}_attraction_wiki",
                    "document": f"{city} sightseeing: {wiki_summary}",
                    "metadata": {
                        "name": f"About {city}",
                        "city": city,
                        "category": "attraction",
                        "rating": 4.5,
                        "interest_tags": ["history", "culture", "sightseeing"]
                    }
                })
            else:
                # 3. Simple baseline description if Wikipedia also fails
                payloads_to_embed.append({
                    "id": f"place_{city.lower()}_attraction_baseline",
                    "document": f"Sightseeing and travel attractions in the beautiful city of {city}, South India.",
                    "metadata": {
                        "name": f"{city} Sightseeing",
                        "city": city,
                        "category": "attraction",
                        "rating": 4.0,
                        "interest_tags": ["sightseeing", "explore"]
                    }
                })
                
    if payloads_to_embed:
        print(f"Adding {len(payloads_to_embed)} place documents to ChromaDB...")
        # Write records into the vector database
        add_places(payloads_to_embed)
        print("Vector database ingestion completed successfully!")
    else:
        print("No places found to embed.")

if __name__ == "__main__":
    run_ingestion()
