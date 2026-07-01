import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import plan_trip

app = FastAPI(
    title="TripSage AI",
    description="Multi-agent travel planning system for South India",
    version="1.0.0"
)

# Configure CORS Middleware (allows our frontend to query the API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(plan_trip.router, prefix="/api", tags=["Itinerary Generation"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the TripSage AI Backend API!"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
