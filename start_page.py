import streamlit as st

# Configure page
st.set_page_config(
    page_title="Equalize NYC",
    page_icon="⚖️",
    layout="centered",
)

# Initialize session state for carousel language selection
if "selected_language" not in st.session_state:
    st.session_state.selected_language = None

# CSS for dark theme and animations
st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        background-color: #0e0e0e;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    }
    
    .main {
        background-color: #0e0e0e;
        padding: 2rem 1rem;
    }
    
    .block-container {
        max-width: 500px;
        padding: 2rem 1rem;
    }
    
    .title-container {
        text-align: center;
        margin-bottom: 3rem;
    }
    
    .title-container h1 {
        font-size: 3rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #a0a0a0;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    /* Carousel Container - Simplified */
    .carousel-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 200px;
        margin: 2rem 0 2rem 0;
        perspective: 1000px;
    }
    
    .carousel-text {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: simpleFade 3s ease-in-out infinite;
    }
    
    @keyframes simpleFade {
        0% {
            opacity: 0;
        }
        20% {
            opacity: 1;
        }
        80% {
            opacity: 1;
        }
        100% {
            opacity: 0;
        }
    }


    
    /* CTA Button styling */
    .stButton > button {
        width: 100%;
        padding: 1rem;
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff !important;
        background-color: #4f46e5 !important;
        border: none !important;
        border-radius: 12px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        margin-top: 2rem;
    }
    
    .stButton > button:hover {
        background-color: #4338ca !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(79, 70, 229, 0.3) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 5px 15px rgba(79, 70, 229, 0.2) !important;
    }
    
    /* Divider styling */
    .divider {
        height: 1px;
        background: linear-gradient(to right, transparent, #4f46e5, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title section
st.markdown("""
<div class="title-container">
    <h1>⚖️ Equalize</h1>
    <p class="subtitle">Fight NYC Violations with AI Advocacy</p>
</div>
""", unsafe_allow_html=True)

# Carousel with language greetings - updated list
greetings = [
    {"text": "Say Hello!", "lang": "en"},
    {"text": "¡Decir Hola!", "lang": "es"},
    {"text": "Скажи привет!", "lang": "ru"},
    {"text": "講你好！", "lang": "yue"},
    {"text": "Diga Olá!", "lang": "pt-br"},
    {"text": "说你好！", "lang": "zh"},
    {"text": "זאג שלום!", "lang": "yi"},
    {"text": "বলুন নমস্কার!", "lang": "bn"},
    {"text": "Di Ciao!", "lang": "it"},
    {"text": "Dites Bonjour!", "lang": "fr"},
    {"text": "Di Bonjou!", "lang": "ht"},
]

# Display carousel animation with rotation
st.markdown("""
<div class="carousel-container">
    <div class="carousel-text" id="carousel-text">Say Hello!</div>
</div>
""", unsafe_allow_html=True)

# JavaScript to cycle through greetings - simple version
st.markdown("""
<script>
const greetings = [
    "Say Hello!",
    "¡Decir Hola!",
    "Скажи привет!",
    "講你好！",
    "Diga Olá!",
    "说你好！",
    "זאג שלום!",
    "বলুন নমস্কার!",
    "Di Ciao!",
    "Dites Bonjour!",
    "Di Bonjou!"
];

let currentIndex = 0;
const carouselEl = document.getElementById("carousel-text");

function updateText() {
    if (carouselEl) {
        carouselEl.textContent = greetings[currentIndex];
        currentIndex = (currentIndex + 1) % greetings.length;
    }
}

if (carouselEl) {
    updateText();
    setInterval(updateText, 3000);
}
</script>
""", unsafe_allow_html=True)

# Store the current greeting language
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

# CTA Button to navigate to main app
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("Get Started →", use_container_width=True, key="start_button"):
        # Use current carousel index to pick language
        current_greeting = greetings[st.session_state.carousel_index % len(greetings)]
        st.session_state.selected_language = current_greeting["lang"]
        st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(greetings)
        
        # Navigate to app page
        st.switch_page("pages/app_page.py")

# Footer section
st.markdown("""
<div style="text-align: center; margin-top: 4rem; color: #707070; font-size: 0.9rem;">
    <p>AI-powered civic advocate for small businesses fighting municipal violations in NYC.</p>
</div>
""", unsafe_allow_html=True)
