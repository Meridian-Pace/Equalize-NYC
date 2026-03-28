import streamlit as st
from ai_engine import get_analysis
from data_manager import load_nyc_rules

st.set_page_config(
    page_title="Equalize NYC",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("⚖️ Equalize NYC")
st.caption("A multimodal civic advocate for small businesses fighting municipal fines.")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(140deg, #f7f9fc 0%, #ffffff 55%, #fff8de 100%);
    }
    .brand-badge {
        display: inline-block;
        background: #003591;
        color: white;
        border-left: 6px solid #F6BE00;
        padding: 0.4rem 0.7rem;
        border-radius: 0.45rem;
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
    }
    </style>
    <div class="brand-badge">Equalize NYC | NYC Blue + NYC Orange</div>
    """,
    unsafe_allow_html=True,
)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = ""

st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📷 Visual Evidence")
    img_file = st.camera_input("Scan Violation")

with right_col:
    st.subheader("📝 Your Concern")
    user_msg = st.text_input("What is your concern?")
    st.audio_input("Optional audio note (placeholder)")

st.divider()

analyze_clicked = st.button("⚖️ Analyze", type="primary", use_container_width=True)

rules_context = load_nyc_rules()

if analyze_clicked:
    if img_file and user_msg:
        with st.spinner("Consulting NYC Law..."):
            try:
                st.session_state.analysis_result = get_analysis(
                    img_file.getvalue(),
                    user_msg,
                    rules_context,
                )
                st.success("Analysis complete.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
    else:
        st.warning("Please provide both an image and your concern before analyzing.")

with st.expander("📜 Raw Legal Rule Context"):
    if rules_context:
        st.text_area(
            label="nyc_rules.txt",
            value=rules_context,
            height=300,
            disabled=True,
        )
    else:
        st.info("No nyc_rules.txt found. Add one to provide compliance context.")

if st.session_state.analysis_result:
    st.subheader("AI Recommendation")
    st.success(st.session_state.analysis_result)
