import os
import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
high_res_camera = components.declare_component("high_res_camera", path=_FRONTEND_DIR)
