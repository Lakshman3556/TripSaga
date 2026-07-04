import streamlit as st
import requests
import time
import os
import sys

# Add project root and backend to python path for local execution / seeding imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

# Automatic bootstrapping of databases if missing
def bootstrap_databases():
    db_path = os.path.join(PROJECT_ROOT, "backend", "data", "distances.db")
    chroma_dir = os.path.join(PROJECT_ROOT, "backend", "data", "chroma_store")
    
    # 1. Initialize SQLite Database
    if not os.path.exists(db_path):
        st.info("📦 First-time setup: Initializing and seeding SQLite distances database...")
        try:
            from backend.data.build_transport_db import populate_db
            populate_db()
            st.success("✅ Distances database successfully seeded!")
        except Exception as e:
            st.error(f"❌ Failed to seed SQLite database: {e}")
            
    # 2. Initialize ChromaDB Vector Store
    if not os.path.exists(chroma_dir) or not os.listdir(chroma_dir):
        st.info("📦 First-time setup: Indexing Wikivoyage travel information into vector store...")
        try:
            from backend.data.ingest_wikivoyage import run_ingestion
            run_ingestion()
            st.success("✅ Vector database successfully initialized!")
        except Exception as e:
            st.error(f"❌ Failed to seed Vector database: {e}")

bootstrap_databases()

# Helper to run pipeline in-process
def run_agent_pipeline_locally(request_data):
    from app.core.guardrails import validate_cities
    from app.graph.workflow import generate_itinerary
    
    is_valid, err_msg = validate_cities(request_data["origin"], request_data["destination"])
    if not is_valid:
        raise ValueError(err_msg)
        
    inputs = {
        "origin": request_data["origin"],
        "destination": request_data["destination"],
        "days": request_data["days"],
        "budget": request_data["budget"],
        "transport_pref": request_data["transport_pref"],
        "interests": request_data["interests"]
    }
    
    result = generate_itinerary(inputs)
    
    if result.get("errors") and any("failed" in err.lower() for err in result["errors"]):
        raise RuntimeError(f"Agent workflow failed: {', '.join(result['errors'])}")
        
    # Construct same dict layout that FastAPI returns
    trip_data = {
        "origin": result["origin"],
        "destination": result["destination"],
        "days": result["days"],
        "budget_limit": result.get("budget"),
        "route": {
            "mode": result["transport_info"]["mode"],
            "duration_hours": result["transport_info"]["duration_hours"],
            "cost_inr": result["transport_info"]["cost_inr"],
            "route_type": result["transport_info"]["route_type"],
            "origin_airport": result["transport_info"]["origin_airport"],
            "destination_airport": result["transport_info"]["destination_airport"],
            "warning": result["transport_info"]["warning"]
        },
        "budget_breakdown": {
            "transport_cost": result["budget_breakdown"]["transport_cost"],
            "hotel_cost": result["budget_breakdown"]["hotel_cost"],
            "food_cost": result["budget_breakdown"]["food_cost"],
            "total_cost": result["budget_breakdown"]["total_cost"]
        },
        "itinerary": {
            day: {
                "morning": plan["morning"],
                "afternoon": plan["afternoon"],
                "evening": plan["evening"],
                "meals": plan["meals"]
            } for day, plan in result["final_itinerary"].items()
        },
        "review_notes": result.get("errors", [])
    }
    return trip_data

# 1. Setup Page Configurations
st.set_page_config(
    page_title="TripSage AI | Multi-Agent Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Curated Custom CSS for Glassmorphism & Travel Theme Aesthetics
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    /* Set custom typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
    }
    
    /* App-wide deep gradient background */
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #1e1b4b 100%) !important;
        color: #f1f5f9 !important;
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(17, 24, 39, 0.9) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(8px) !important;
    }
    
    /* Glassmorphic Panel Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.12);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    /* Neon Glow Badges & Accents */
    .highlight-glow {
        color: #818cf8;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(129, 140, 248, 0.4);
    }
    
    .timeline-node {
        border-left: 3px dashed #6366f1;
        padding-left: 20px;
        margin-left: 10px;
        position: relative;
        margin-bottom: 20px;
    }
    
    .timeline-node::before {
        content: '';
        position: absolute;
        width: 14px;
        height: 14px;
        background-color: #818cf8;
        border: 3px solid #090d16;
        border-radius: 50%;
        left: -9px;
        top: 4px;
        box-shadow: 0 0 8px #818cf8;
    }
    
    /* Metrics blocks styling */
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 28px;
        font-weight: 700;
        color: #f8fafc;
    }
    
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Premium button */
    .stButton>button {
        background: linear-gradient(90deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.5) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Static Mapping of South Indian States and their respective Supported Cities
STATE_CITY_MAP = {
    "Telangana": ["Hyderabad", "Warangal", "Nagarjuna Sagar", "Bhadrachalam", "Nizamabad", "Karimnagar", "Khammam", "Nalgonda", "Mahabubnagar", "Adilabad", "Medak", "Ramagundam", "Yadadri", "Vemulawada", "Alampur"],
    "Karnataka": ["Bengaluru", "Mysore", "Hampi", "Coorg", "Gokarna", "Chikmagalur", "Mangalore", "Udupi", "Badami", "Dandeli", "Kabini", "Murudeshwar", "Belur", "Halebidu"],
    "Kerala": ["Kochi", "Munnar", "Alleppey", "Wayanad", "Varkala", "Thiruvananthapuram", "Kovalam", "Thekkady", "Kumarakom", "Athirappilly", "Kozhikode"],
    "Tamil Nadu": ["Chennai", "Madurai", "Ooty", "Pondicherry", "Kanyakumari", "Rameshwaram", "Kodaikanal", "Mahabalipuram", "Kanchipuram", "Tanjore", "Trichy", "Yercaud", "Coimbatore", "Vellore"],
    "Andhra Pradesh": ["Visakhapatnam", "Tirupati", "Araku Valley", "Vijayawada", "Anantapur", "Nellore", "Kurnool", "Rajahmundry", "Kakinada", "Guntur", "Srisailam", "Amaravati", "Horsley Hills", "Lepakshi", "Gandikota"]
}

# --- HEADER SECTION ---
st.markdown("<h1 style='text-align: center; margin-top: 10px;'>✈️ <span class='highlight-glow'>TRIPSAGE AI</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 16px; margin-bottom: 30px;'>Multi-Agent Travel Planner for South India</p>", unsafe_allow_html=True)

# --- SIDEBAR: TRIP PLANNER PARAMETERS ---
with st.sidebar:
    st.markdown("<h3 style='color: #818cf8; margin-bottom: 20px;'>Plan Your Route</h3>", unsafe_allow_html=True)
    
    # Dependent Dropdown: Origin
    orig_state = st.selectbox("Origin State", list(STATE_CITY_MAP.keys()), index=0)
    origin = st.selectbox("Origin City", STATE_CITY_MAP[orig_state])
    
    # Dependent Dropdown: Destination
    dest_state = st.selectbox("Destination State", list(STATE_CITY_MAP.keys()), index=2)
    destination = st.selectbox("Destination City", STATE_CITY_MAP[dest_state])
    
    st.markdown("---")
    st.markdown("<h3 style='color: #818cf8;'>Trip Settings</h3>", unsafe_allow_html=True)
    
    # Trip length and budget
    days = st.slider("Duration (Days)", min_value=1, max_value=7, value=3)
    
    budget_enabled = st.checkbox("Specify Budget Limit?", value=False)
    budget = None
    if budget_enabled:
        budget = st.number_input("Maximum Budget (INR)", min_value=1000, max_value=100000, value=15000, step=1000)
        
    transport_pref = st.selectbox(
        "Preferred Travel Mode",
        options=["car", "bus", "train", "flight"],
        format_func=lambda x: f"🚗 {x.title()}" if x=="car" else f"🚌 {x.title()}" if x=="bus" else f"🚂 {x.title()}" if x=="train" else f"✈️ {x.title()}"
    )
    
    interests = st.multiselect(
        "Your Travel Interests",
        options=["temples", "history", "nature", "palace", "explore", "spiritual", "monument", "breakfast", "biryani", "non-vegetarian", "vegetarian"],
        default=["history", "nature"]
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    trigger_plan = st.button("Generate My Itinerary", use_container_width=True)

# --- MAIN DISPLAY PANEL ---
if trigger_plan:
    # 1. API Call payload creation
    request_data = {
        "origin": origin,
        "destination": destination,
        "days": days,
        "budget": budget,
        "transport_pref": transport_pref,
        "interests": interests
    }
    
    # Loading animation
    with st.status("🔮 Orchestrating multi-agent graph nodes...", expanded=True) as status_indicator:
        st.write("Initializing agents: loading [TripState]...")
        time.sleep(1.0)
        
        st.write("🤖 [Planner Agent]: Constructing semantic retrieval queries...")
        time.sleep(1.5)
        
        st.write("📚 [Knowledge Retriever]: Performing similarity search over ChromaDB...")
        time.sleep(1.5)
        
        st.write("📊 [Transport & Budget]: Querying SQLite distances & computing budget breakdown...")
        time.sleep(1.0)
        
        st.write("✍️ [Itinerary Composer]: Sequencing days and creating day-wise plan...")
        time.sleep(2.0)
        
        st.write("🛡️ [Reviewer Agent]: Verifying timeline boundaries and checking budget limits...")
        
        # Trigger plan generation (API client or Local Agent fallback)
        try:
            backend_url = os.environ.get("TRIPSAGE_BACKEND_URL", "http://127.0.0.1:8000")
            use_remote = False
            
            if backend_url:
                try:
                    # Quick health check to see if remote API is active
                    health_check_url = backend_url.rstrip("/") + "/"
                    r = requests.get(health_check_url, timeout=1.5)
                    if r.status_code == 200:
                        use_remote = True
                except Exception:
                    pass
            
            if use_remote:
                st.write(f"🌐 Querying backend API at {backend_url}...")
                response = requests.post(f"{backend_url.rstrip('/')}/api/plan", json=request_data, timeout=60.0)
                if response.status_code == 200:
                    trip_data = response.json()
                else:
                    err_detail = response.json().get("detail", "Unknown server error.")
                    raise RuntimeError(f"API returned error: {err_detail}")
            else:
                st.write("🔌 Running agent workflow in-process...")
                trip_data = run_agent_pipeline_locally(request_data)
                
            status_indicator.update(label="✨ Itinerary generated successfully!", state="complete", expanded=False)
            
            # --- RENDER RESULTS IN MAIN SECTION ---
            col1, col2 = st.columns([1, 2], gap="large")
            
            # Column 1: Transport and Budget Glassmorphic Details Card
            with col1:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown(f"<h3>Route & Logistics</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #94a3b8;'>Traveling from <b>{trip_data['origin']}</b> to <b>{trip_data['destination']}</b></p>", unsafe_allow_html=True)
                
                # Transit Metrics
                metric_cols = st.columns(2)
                with metric_cols[0]:
                    st.markdown(f"<div class='metric-label'>Transport Mode</div><div class='metric-value'>{trip_data['route']['mode'].title()}</div>", unsafe_allow_html=True)
                with metric_cols[1]:
                    st.markdown(f"<div class='metric-label'>Duration</div><div class='metric-value'>{trip_data['route']['duration_hours']} hrs</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if trip_data['route']['warning']:
                    st.warning(f"⚠️ {trip_data['route']['warning']}")
                if trip_data['route']['origin_airport'] or trip_data['route']['destination_airport']:
                    st.markdown("<div style='background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 15px;'>", unsafe_allow_html=True)
                    st.markdown("<span style='font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;'>Transit Hubs</span>", unsafe_allow_html=True)
                    if trip_data['route']['origin_airport']:
                        st.markdown(f"<p style='margin: 4px 0; font-size: 14px;'>🛫 <b>Origin Airport:</b><br><span style='color: #cbd5e1;'>{trip_data['route']['origin_airport']}</span></p>", unsafe_allow_html=True)
                    if trip_data['route']['destination_airport']:
                        st.markdown(f"<p style='margin: 4px 0; font-size: 14px;'>🛬 <b>Destination Airport:</b><br><span style='color: #cbd5e1;'>{trip_data['route']['destination_airport']}</span></p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                # -----------------------------------------------------------------
                
                # Cost Metrics
                st.markdown("<h4>Estimated Budget</h4>", unsafe_allow_html=True)
                st.markdown(f"<p class='metric-label'>Hotel Stay (Total)</p><p class='metric-value' style='font-size:24px; color:#818cf8;'>₹{trip_data['budget_breakdown']['hotel_cost']}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='metric-label'>Transport (Roundtrip)</p><p class='metric-value' style='font-size:24px; color:#818cf8;'>₹{trip_data['budget_breakdown']['transport_cost']}</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='metric-label'>Food (Total)</p><p class='metric-value' style='font-size:24px; color:#818cf8;'>₹{trip_data['budget_breakdown']['food_cost']}</p>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(f"<p class='metric-label'>Total Estimate</p><p class='metric-value' style='font-size:32px; color:#10b981;'>₹{trip_data['budget_breakdown']['total_cost']}</p>", unsafe_allow_html=True)
                
                # Display budget check indicator
                if trip_data['budget_limit']:
                    if trip_data['budget_breakdown']['total_cost'] <= trip_data['budget_limit']:
                        st.success("✅ Within your budget limit!")
                    else:
                        st.warning("⚠️ Exceeds your budget limit!")
                
                # Display reviewer guardrail adjustments notes
                if trip_data['review_notes']:
                    st.markdown("<br><b>Reviewer Adjustments:</b>", unsafe_allow_html=True)
                    for note in trip_data['review_notes']:
                        st.info(f"💡 {note}")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Column 2: Interactive Day-wise Timeline rendering
            with col2:
                st.markdown("<h3 style='margin-bottom:20px;'>Your Personalized Timeline</h3>", unsafe_allow_html=True)
                
                # Sort days sequentially
                sorted_days = sorted(trip_data['itinerary'].keys(), key=lambda x: int(x.split()[1]))
                
                for day_key in sorted_days:
                    day_plan = trip_data['itinerary'][day_key]
                    
                    st.markdown(f"<div class='glass-card'>", unsafe_allow_html=True)
                    st.markdown(f"<h3 style='color:#818cf8; margin-bottom:15px;'>{day_key}</h3>", unsafe_allow_html=True)
                    
                    # Morning activity
                    st.markdown("<div class='timeline-node'>", unsafe_allow_html=True)
                    st.markdown(f"<b>🌅 Morning</b><br><span style='color:#cbd5e1;'>{day_plan['morning']}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Afternoon activity
                    st.markdown("<div class='timeline-node'>", unsafe_allow_html=True)
                    st.markdown(f"<b>☀️ Afternoon</b><br><span style='color:#cbd5e1;'>{day_plan['afternoon']}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Evening activity
                    st.markdown("<div class='timeline-node'>", unsafe_allow_html=True)
                    st.markdown(f"<b>🌙 Evening</b><br><span style='color:#cbd5e1;'>{day_plan['evening']}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Culinary stops
                    st.markdown("<div class='timeline-node' style='border-left:none; padding-left:12px; margin-left:12px;'>", unsafe_allow_html=True)
                    st.markdown(f"<b>🍽️ Local Eats</b>", unsafe_allow_html=True)
                    for meal_type, recommendation in day_plan['meals'].items():
                        st.markdown(f"<span style='color:#94a3b8; font-size:13px;'>• <i>{meal_type.title()}</i>: {recommendation}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
        except Exception as run_err:
            status_indicator.update(label="❌ Generation failed!", state="error")
            st.error(f"Failed to generate trip plan: {run_err}")
else:
    # Display a beautiful splash page/placeholder card when the user hasn't generated anything yet
    st.markdown("<div class='glass-card' style='text-align: center; max-width: 700px; margin: 40px auto; padding: 40px;'>", unsafe_allow_html=True)
    st.markdown("<h3>Ready to start your adventure?</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Adjust the trip preferences on the left sidebar and click 'Generate My Itinerary'. Our 5-Agent pipeline will dynamically coordinate to construct your perfect route, budget, and day-wise schedule!</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
