import streamlit as st
import base64

# MUST BE THE FIRST COMMAND
st.set_page_config(
    page_title="TransitIQ - Traffic Dashboard", 
    layout="wide", 
    page_icon="🚦"
)

# ---------------- 1. THE LOGO SOLUTION (ADAPTIVE) ----------------
def get_svg_logo():
    svg = """
    <svg width="250" height="80" viewBox="0 0 250 80" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="45" font-family="sans-serif" font-size="38" font-weight="900" fill="white" style="letter-spacing:-1.5px;">Transit</text>
        <text x="135" y="45" font-family="sans-serif" font-size="38" font-weight="900" fill="#1eb53a" style="letter-spacing:-1.5px;">IQ</text>
        <text x="2" y="65" font-family="sans-serif" font-size="10" font-weight="700" fill="#64748b" style="letter-spacing:1.5px; text-transform:uppercase;">Smart Traffic System</text>
    </svg>
    """
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

# ---------------- 2. THE FULL ADAPTIVE UI STYLE ----------------
st.markdown("""
<style>
    /* 1. Sidebar Theme Adjustment */
    [data-testid="stSidebar"] {
        background-color: #0e1117 !important;
        border-right: none;
    }

    /* 2. Logo Alignment */
    [data-testid="stLogo"] {
        margin-left: 12px !important; 
        height: 100px !important;
        margin-top: 10px !important;
    }

    /* 3. The Navigation "Card" */
    [data-testid="stSidebarNav"] {
        background-color: #000000 !important; 
        margin: 0 12px !important;
        padding: 15px 5px !important;
        border-radius: 15px;
        border: 1px solid #222222;
    }

    /* 4. Text Selection Fix (Light & Dark Mode) */
    [data-testid="stSidebarNavItems"] li div span {
        color: #94a3b8 !important;
    }

    [data-testid="stSidebarNavItems"] li div[aria-selected="true"] {
        background-color: #1eb53a !important; 
        border-radius: 10px !important;
    }

    [data-testid="stSidebarNavItems"] li div[aria-selected="true"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 5. FULL WIDTH PAGE FOOTER (Main Content Area) */
    .main-footer {
        width: 100%;
        padding: 20px 0;
        margin-top: 50px;
        border-top: 1px solid #222222;
        text-align: center;
        background-color: transparent;
    }
    
    .footer-text {
        color: #64748b;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- 3. BRANDING & NAVIGATION ----------------

st.logo(get_svg_logo())

home = st.Page("pages/home.py", title="Home", icon="🏠")
forecast = st.Page("pages/forecast.py", title="Forecast", icon="🔮")
analysis = st.Page("pages/analysis.py", title="Analysis", icon="📊")
routes = st.Page("pages/routes.py", title="Routes", icon="🛣️")
incidents = st.Page("pages/incidents.py", title="Incidents", icon="⚠️")
about = st.Page("pages/about.py", title="About", icon="ℹ️")

pg = st.navigation({
    "System": [home, forecast],
    "Intelligence": [analysis, routes, incidents],
    "Project": [about]
})

# ---------------- 4. EXECUTION & FOOTER PLACEMENT ----------------

# Run the selected page
pg.run()

# The footer is placed AFTER pg.run() so it always appears at the 
# bottom of whatever page is currently loaded in the main area.
st.markdown("""
    <footer>
        <span class="footer-text">
            © 2026 TransitIQ | Smart Traffic Congestion Prediction System | MCA Group B2511
        </span>
    </footer>
""", unsafe_allow_html=True)