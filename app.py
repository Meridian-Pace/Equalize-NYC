import os
import streamlit as st
from ai_engine import CivicAI
from data_manager import get_context_block, load_rules

st.set_page_config(
    page_title="Equalize NYC",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("⚖️ Equalize NYC")
st.caption("A multimodal civic advocate for small businesses fighting municipal fines.")

st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📷 Visual Evidence")
    camera_image = st.camera_input("Capture the violation or fine notice")

with right_col:
    st.subheader("🎙️ Your Question")
    audio_input = st.audio_input("Describe the situation or ask your question")

st.divider()

analyze_clicked = st.button("⚖️ Check Compliance", type="primary", use_container_width=True)

if analyze_clicked:
    image_bytes = None
    if camera_image is not None:
        image_bytes = camera_image.getvalue()

    voice_text = None
    if audio_input is not None:
        # audio_input is a BytesIO-like object; pass the raw bytes to the AI
        # For transcription, Gemini handles audio inline — future enhancement.
        # For now, use a default prompt so the model still analyzes any image.
        voice_text = "Analyze this violation image and tell me every way I can fight this fine."

    context_text = get_context_block()

    if image_bytes is None and voice_text is None and not context_text:
        st.warning("Please provide at least an image or audio input before analyzing.")
    else:
        with st.spinner("Consulting NYC compliance rules..."):
            try:
                credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
                ai = CivicAI(credentials_path=credentials_path)
                recommendation = ai.analyze_incident(
                    image_bytes=image_bytes,
                    voice_text=voice_text,
                    context_text=context_text if context_text else None,
                )

                st.success("Analysis complete.")

                with st.expander("📜 Raw Legal Rule Context"):
                    raw_rules = load_rules()
                    if raw_rules:
                        st.text_area(
                            label="nyc_rules.txt",
                            value=raw_rules,
                            height=300,
                            disabled=True,
                        )
                    else:
                        st.info("No nyc_rules.txt found. Add one to provide compliance context.")

                st.subheader("AI Recommendation")
                st.success(recommendation)

            except Exception as e:
                st.error(f"Analysis failed: {e}")
