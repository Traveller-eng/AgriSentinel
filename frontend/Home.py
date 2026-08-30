"""
AgriSentinel - Crop-Health Surveillance Platform
Landing Page & Role Switcher
Smart India Hackathon MVP
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add frontend directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from utils.styling import (
    get_global_css,
    render_header,
    render_card,
    render_badge,
    BRAND_GREEN,
    ACCENT_TERRACOTTA,
    INK,
    INK_SECONDARY,
    SURFACE,
    BORDER,
    FONT_HEADING,
    FONT_BODY
)
from utils.i18n import t, render_language_selector

st.set_page_config(
    page_title="AgriSentinel | Crop-Health Surveillance",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject Global Visual Theme
st.markdown(get_global_css(), unsafe_allow_html=True)

# Top Bar Branding & Language Selector
top_col1, top_col2 = st.columns([2, 1], gap="medium")
with top_col1:
    st.markdown(f"""
    <div style="background-color: {BRAND_GREEN}; padding: 0.65rem 1.25rem; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; color: white;">
        <div style="display: flex; align-items: center; gap: 0.65rem;">
            <span style="font-size: 1.3rem;">🌱</span>
            <span style="font-family: '{FONT_HEADING}', serif; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.02em;">{t("app_name")}</span>
        </div>
        <div style="font-family: '{FONT_BODY}', sans-serif; font-size: 0.8rem; opacity: 0.9; font-weight: 500;">
            {t("kharif_surveillance")}
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_col2:
    st.markdown("<div style='margin-top: 0.15rem;'></div>", unsafe_allow_html=True)
    render_language_selector(key_prefix="home")

# Main Hero Header
st.markdown(f"""
<div style="text-align: center; margin: 1.5rem 0 2.5rem 0;">
    <div class="ags-eyebrow">{t("sih_eyebrow")}</div>
    <h1 class="ags-h1" style="font-size: 2.5rem; margin-bottom: 0.75rem;">{t("home_title")}</h1>
    <p class="ags-subtitle" style="font-size: 1.05rem; max-width: 680px; margin: 0 auto; color: {INK_SECONDARY};">
        {t("home_subtitle")}
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-bottom: 1rem;">
    <span class="ags-eyebrow">{t("select_role_eyebrow")}</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(f"""
    <div class="ags-card" style="height: 320px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-size: 1.8rem;">👨‍🌾</span>
                {render_badge(t("farmer_portal_badge"), BRAND_GREEN)}
            </div>
            <h3 class="ags-h3" style="margin-bottom: 0.4rem;">{t("farmer_card_title")}</h3>
            <p class="ags-caption" style="font-size: 0.875rem; line-height: 1.5; color: {INK_SECONDARY};">
                {t("farmer_card_desc")}
            </p>
        </div>
        <div style="margin-top: 1rem;">
            <div style="font-size: 0.8rem; color: {BRAND_GREEN}; font-weight: 600; margin-bottom: 0.75rem;">
                {t("farmer_card_bullet1")}<br>
                {t("farmer_card_bullet2")}<br>
                {t("farmer_card_bullet3")}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(t("open_farmer_btn"), key="btn_farmer", use_container_width=True):
        st.switch_page("pages/1_Farmer.py")

with col2:
    st.markdown(f"""
    <div class="ags-card" style="height: 320px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-size: 1.8rem;">📋</span>
                {render_badge(t("ext_portal_badge"), ACCENT_TERRACOTTA)}
            </div>
            <h3 class="ags-h3" style="margin-bottom: 0.4rem;">{t("ext_card_title")}</h3>
            <p class="ags-caption" style="font-size: 0.875rem; line-height: 1.5; color: {INK_SECONDARY};">
                {t("ext_card_desc")}
            </p>
        </div>
        <div style="margin-top: 1rem;">
            <div style="font-size: 0.8rem; color: {ACCENT_TERRACOTTA}; font-weight: 600; margin-bottom: 0.75rem;">
                {t("ext_card_bullet1")}<br>
                {t("ext_card_bullet2")}<br>
                {t("ext_card_bullet3")}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(t("open_ext_btn"), key="btn_ext", use_container_width=True):
        st.switch_page("pages/2_Extension_Worker.py")

with col3:
    st.markdown(f"""
    <div class="ags-card" style="height: 320px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-size: 1.8rem;">🏛️</span>
                {render_badge(t("off_portal_badge"), "#2B2A26")}
            </div>
            <h3 class="ags-h3" style="margin-bottom: 0.4rem;">{t("off_card_title")}</h3>
            <p class="ags-caption" style="font-size: 0.875rem; line-height: 1.5; color: {INK_SECONDARY};">
                {t("off_card_desc")}
            </p>
        </div>
        <div style="margin-top: 1rem;">
            <div style="font-size: 0.8rem; color: {INK}; font-weight: 600; margin-bottom: 0.75rem;">
                {t("off_card_bullet1")}<br>
                {t("off_card_bullet2")}<br>
                {t("off_card_bullet3")}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(t("open_off_btn"), key="btn_off", use_container_width=True):
        st.switch_page("pages/3_Official_Dashboard.py")

# Bottom Footer
st.markdown("---")
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: {INK_SECONDARY}; padding: 0.5rem 0;">
    <div>{t("footer_text")}</div>
    <div>{t("design_token_note")}</div>
</div>
""", unsafe_allow_html=True)
