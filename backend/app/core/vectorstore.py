import os
import chromadb
from typing import List, Dict, Any, Optional
from app.core.embeddings import LocalMiniLMEmbeddings

# Define path for persistent local Chroma database
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chroma_store")

# Initialize file-based Chroma client
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# Initialize local embedding transformer
embedding_model = LocalMiniLMEmbeddings()

def get_collection():
    """
    Retrieves or initializes the South India places collection in ChromaDB.
    Configured with cosine distance metric.
    """
    return chroma_client.get_or_create_collection(
        name="south_india_places",
        metadata={"hnsw:space": "cosine"}
    )

def add_places(places: List[Dict[str, Any]]) -> None:
    """
    Seeds a list of places into ChromaDB.
    
    Input place dictionary format:
        {
            "id": "place_madurai_attraction_0",
            "document": "Meenakshi Amman Temple is a historic site in Madurai...",
            "metadata": {
                "name": "Meenakshi Amman Temple",
                "city": "Madurai",
                "category": "attraction",
                "rating": 4.8,
                "interest_tags": ["temples", "history", "culture"]
            }
        }
    """
    collection = get_collection()
    
    ids = []
    documents = []
    metadatas = []
    embeddings = []
    
    for place in places:
        metadata = place["metadata"].copy()
        
        # Serialization: Chroma DB metadata only supports simple primitive types (str, int, float, bool).
        # We convert the list of interest_tags to a comma-separated string before storing.
        if "interest_tags" in metadata and isinstance(metadata["interest_tags"], list):
            metadata["interest_tags"] = ",".join(metadata["interest_tags"])
            
        ids.append(place["id"])
        documents.append(place["document"])
        metadatas.append(metadata)
        
        # Calculate embedding vector for the document chunk
        vector = embedding_model.embed_query(place["document"])
        embeddings.append(vector)
        
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

def query_places(query_text: str, city: str, category: Optional[str] = None, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Performs cosine similarity search over places, filtered strictly by city.
    
    Example Input:
        query_places(query_text="historical temples", city="Madurai", category="attraction")
    """
    collection = get_collection()
    query_vector = embedding_model.embed_query(query_text)
    
    # Enforce strict metadata filtering by city
    where_filter = {"city": city}
    if category:
        where_filter["category"] = category
        
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        where=where_filter
    )
    
    formatted_results = []
    if results and results["documents"] and len(results["documents"][0]) > 0:
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]
        
        for i in range(len(docs)):
            meta = metas[i].copy()
            # Deserialization: Convert comma-separated string back to list of interest tags
            if "interest_tags" in meta:
                meta["interest_tags"] = meta["interest_tags"].split(",")
                
            formatted_results.append({
                "id": ids[i],
                "document": docs[i],
                "metadata": meta,
                "distance": distances[i]
            })
            
    return formatted_results
