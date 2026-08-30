"""
AgriSentinel - Farmer Portal (Part A)
Crop Health Check & Autonomous Disease Diagnosis
"""

import streamlit as st
import os
import sys
import uuid
import logging
from pathlib import Path
from PIL import Image

# Ensure paths are configured
current_dir = Path(__file__).resolve().parent
frontend_dir = current_dir.parent
root_dir = frontend_dir.parent
for p in [str(frontend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.styling import (
    get_global_css,
    render_header,
    render_badge,
    render_card,
    render_empty_state,
    get_risk_color,
    BRAND_GREEN,
    ACCENT_TERRACOTTA,
    INK,
    INK_SECONDARY,
    SURFACE,
    BORDER,
    FONT_HEADING,
    FONT_BODY
)
from utils.kb_lookup import get_advisory
from utils.i18n import t, render_language_selector

# --- SWITCHABLE IMPORTS (Real Backend/ML vs Mock Fallback) ---
USE_MOCKS = False

try:
    if USE_MOCKS:
        raise ImportError("Forced mock usage via USE_MOCKS=True")
    from backend.db_ops import insert_report, evaluate_and_update_risk
    from backend.models import DISEASE_CLASSES, GROWTH_STAGES
    from ml.predict import predict
    from ml.gradcam import generate_gradcam
except Exception as e:
    logging.info(f"Using frontend.mocks due to: {e}")
    from mocks import (
        insert_report,
        evaluate_and_update_risk,
        DISEASE_CLASSES,
        GROWTH_STAGES,
        predict,
        generate_gradcam,
        MAHARASHTRA_VILLAGES
    )

st.set_page_config(
    page_title="Crop Health Check | AgriSentinel",
    page_icon="🌱",
    layout="centered"
)

st.markdown(get_global_css(), unsafe_allow_html=True)

# Fixed Constant Crop
CROP_NAME = "Tomato"

# Hardcoded Maharashtra Village Coordinate Map
VILLAGE_COORDINATES = {
    "Wardha (HQ)": (20.7453, 78.6022, "Wardha"),
    "Hinganghat": (20.5524, 78.8358, "Wardha"),
    "Arvi": (20.9840, 78.2323, "Wardha"),
    "Seloo": (20.8358, 78.7061, "Wardha"),
    "Deoli": (20.6621, 78.4795, "Wardha"),
    "Samudrapur": (20.5894, 79.0305, "Wardha"),
    "Karanja Ghadge": (21.1963, 78.5878, "Wardha"),
    "Ashti": (21.2057, 78.1818, "Wardha"),
}

# --- PAGE HEADER WITH LANGUAGE SELECTOR ---
hdr_col1, hdr_col2 = st.columns([1.6, 1.2], gap="small")
with hdr_col1:
    st.markdown(f"""
    <div style="margin-bottom: 0.25rem;">
        <div class="ags-eyebrow">{t("farmer_eyebrow")}</div>
        <h1 class="ags-h1" style="display: flex; align-items: center; gap: 0.5rem; font-size: 1.85rem; margin-bottom: 0;">
            <span style="color: {BRAND_GREEN};">🍃</span> {t("crop_health_check")}
        </h1>
    </div>
    """, unsafe_allow_html=True)

with hdr_col2:
    st.markdown("<div style='margin-top: 0.35rem;'></div>", unsafe_allow_html=True)
    render_language_selector(key_prefix="farmer")

st.markdown(f"""
<div class="ags-crop-pill" style="margin-top: 0.5rem;">
    <span>ⓘ</span> {t("crop_label")}
</div>
""", unsafe_allow_html=True)

# --- FORM INPUTS CARD ---
with st.container():
    st.markdown(f"""
    <div class="ags-card">
        <div class="ags-eyebrow">{t("field_context_eyebrow")}</div>
    """, unsafe_allow_html=True)

    col_v, col_f = st.columns([1.2, 1])
    with col_v:
        selected_village = st.selectbox(
            t("village_location_label"),
            options=list(VILLAGE_COORDINATES.keys()),
            index=0,
            help=t("village_location_help")
        )
    with col_f:
        farm_id_input = st.text_input(
            t("farm_id_label"),
            value="F-4412",
            placeholder="F-XXXX",
            help=t("farm_id_help")
        )

    # Growth Stage selection with translated display labels mapped to English backend values
    st.markdown(f"<div style='font-size: 0.8rem; font-weight: 600; color: #6B6558; margin-top: 0.5rem;'>{t('growth_stage_label')}</div>", unsafe_allow_html=True)
    
    # Display label mapping
    stage_display_to_eng = {t(f"growth_stage_{stage}"): stage for stage in GROWTH_STAGES}
    display_options = list(stage_display_to_eng.keys())
    
    default_idx = 2 if "Flowering" in GROWTH_STAGES else 0
    selected_display_stage = st.radio(
        t("growth_stage_label"),
        options=display_options,
        index=default_idx,
        horizontal=True,
        label_visibility="collapsed"
    )
    # Map back to English constant for backend
    growth_stage = stage_display_to_eng.get(selected_display_stage, "Flowering")

    st.markdown("</div>", unsafe_allow_html=True)

# --- IMAGE UPLOADER SECTION ---
st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    t("upload_prompt"),
    type=["jpg", "jpeg", "png"],
    help=t("upload_help")
)

if not uploaded_file:
    # Gentle empty state prompt matching Figma design
    st.markdown(f"""
    <div class="ags-card-dashed">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem; color: {INK_SECONDARY};">📷</div>
        <div style="font-family: '{FONT_HEADING}', serif; font-size: 1.15rem; font-weight: 600; color: {INK}; margin-bottom: 0.35rem;">
            {t("upload_prompt")}
        </div>
        <div class="ags-caption" style="max-width: 440px; margin: 0 auto 1rem auto;">
            {t("upload_desc")}
        </div>
        <div style="display: flex; justify-content: center; gap: 0.5rem;">
            <span class="ags-badge" style="background-color: #EFEBE4; color: {INK_SECONDARY};">.jpg</span>
            <span class="ags-badge" style="background-color: #EFEBE4; color: {INK_SECONDARY};">.png</span>
            <span class="ags-badge" style="background-color: #EFEBE4; color: {INK_SECONDARY};">.jpeg</span>
        </div>
    </div>
    <div class="ags-caption" style="text-align: center; margin-top: 0.5rem; color: {INK_SECONDARY};">
        {t("ai_disclaimer")}
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Show image preview
preview_col1, preview_col2 = st.columns([1, 1.5])
with preview_col1:
    st.image(uploaded_file, caption=t("selected_leaf_caption"), use_container_width=True)

diagnose_btn = st.button(t("diagnose_button"), use_container_width=True, type="primary")

# Execute Diagnosis Pipeline on Button Click
if diagnose_btn or "diagnosis_result" in st.session_state:
    if diagnose_btn:
        with st.spinner(t("analyzing_spinner")):
            try:
                # 1. Save uploaded file to images/
                img_dir = Path("images")
                img_dir.mkdir(parents=True, exist_ok=True)
                file_ext = Path(uploaded_file.name).suffix or ".jpg"
                unique_filename = f"leaf_{uuid.uuid4().hex[:10]}{file_ext}"
                saved_image_path = str(img_dir / unique_filename)

                with open(saved_image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 2. ML Prediction
                pred_result = predict(saved_image_path)
                predicted_disease = pred_result.get("predicted_disease", "Early Blight")
                confidence = float(pred_result.get("confidence", 0.85))

                # 3. Grad-CAM generation (non-blocking)
                gradcam_path = None
                try:
                    gradcam_path = generate_gradcam(saved_image_path, predicted_disease)
                except Exception as e_gc:
                    logging.warning(f"Grad-CAM generation failed: {e_gc}")
                    gradcam_path = None

                # 4. Extract Coordinates & District
                lat, lon, district = VILLAGE_COORDINATES.get(
                    selected_village,
                    (20.7453, 78.6022, "Wardha")
                )

                # 5. Insert Report into DB
                report_id = insert_report(
                    farm_id=farm_id_input.strip() or "F-4412",
                    image_path=saved_image_path,
                    crop=CROP_NAME,
                    growth_stage=growth_stage,
                    predicted_disease=predicted_disease,
                    confidence=confidence,
                    lat=lat,
                    lon=lon,
                    district=district,
                    gradcam_path=gradcam_path
                )

                # 6. Evaluate Risk & Fetch Checklist
                risk_level, checklist = evaluate_and_update_risk(report_id)

                # 7. Query Knowledge Base
                advisory = get_advisory(predicted_disease)

                # Cache in session state
                st.session_state["diagnosis_result"] = {
                    "report_id": report_id,
                    "predicted_disease": predicted_disease,
                    "confidence": confidence,
                    "risk_level": risk_level,
                    "checklist": checklist,
                    "advisory": advisory,
                    "saved_image_path": saved_image_path,
                    "gradcam_path": gradcam_path,
                    "growth_stage": growth_stage,
                    "village": selected_village
                }
            except Exception as ex:
                logging.error(f"Error during crop diagnosis: {ex}", exc_info=True)
                st.error(t("diag_error"))
                st.stop()

    # Retrieve Diagnosis from Session State
    res = st.session_state.get("diagnosis_result")
    if not res:
        st.stop()

    predicted_disease = res["predicted_disease"]
    conf_pct = int(res["confidence"] * 100)
    risk_level = res["risk_level"]
    checklist = res["checklist"]
    advisory = res["advisory"]
    gradcam_path = res["gradcam_path"]
    risk_color = get_risk_color(risk_level)

    st.markdown("---")

    # --- CASE A: HEALTHY CROP ---
    if "Healthy" in predicted_disease:
        st.markdown(f"""
        <div class="ags-card" style="border-left: 4px solid {BRAND_GREEN}; background-color: #F4F8F4;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="ags-eyebrow" style="color: {BRAND_GREEN};">{t("health_eval_eyebrow")}</div>
                    <h2 class="ags-h2" style="color: {BRAND_GREEN}; margin-bottom: 0.25rem;">{t("crop_healthy_title")}</h2>
                    <div style="font-style: italic; font-size: 0.875rem; color: {INK_SECONDARY};">Solanum lycopersicum</div>
                </div>
                {render_badge(t("healthy_low_risk"), BRAND_GREEN)}
            </div>
            <div style="margin-top: 1.25rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600;">
                    <span>{t("model_confidence")}</span>
                    <span>{conf_pct}%</span>
                </div>
                <div style="background-color: #E2E8E2; height: 6px; border-radius: 3px; margin: 0.4rem 0 0.5rem 0; overflow: hidden;">
                    <div style="background-color: {BRAND_GREEN}; width: {conf_pct}%; height: 100%;"></div>
                </div>
                <div class="ags-caption">{t("healthy_micro_explainer")}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="ags-card">
            <div class="ags-eyebrow">{t("monitoring_rec_eyebrow")}</div>
            <p class="ags-body">
                {t("healthy_monitoring_desc")}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- CASE B: DISEASE DETECTED ---
    else:
        sci_name = advisory.get("scientific_name", "Solanaceae pathogen")
        st.markdown(f"""
        <div class="ags-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                <div>
                    <div class="ags-eyebrow">{t("detected_disease_eyebrow")}</div>
                    <h2 class="ags-h2" style="margin-bottom: 0.15rem;">{predicted_disease}</h2>
                    <div style="font-style: italic; font-size: 0.875rem; color: {INK_SECONDARY};">{sci_name}</div>
                </div>
                <div>
                    {render_badge(risk_level, risk_color)}
                </div>
            </div>
            <div style="margin-top: 1.25rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.875rem; font-weight: 600; color: {INK};">
                    <span>{t("confidence_label")}</span>
                    <span>{conf_pct}%</span>
                </div>
                <div style="background-color: #EBE6DC; height: 7px; border-radius: 4px; margin: 0.45rem 0 0.5rem 0; overflow: hidden;">
                    <div style="background-color: {ACCENT_TERRACOTTA}; width: {conf_pct}%; height: 100%;"></div>
                </div>
                <div class="ags-caption" style="color: {INK_SECONDARY};">
                    {t("micro_explainer")}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Grad-CAM heatmap visualization
        if gradcam_path and os.path.exists(gradcam_path):
            with st.expander(t("gradcam_expander"), expanded=False):
                gc_col1, gc_col2 = st.columns(2)
                with gc_col1:
                    st.image(res["saved_image_path"], caption=t("original_sample_caption"), use_container_width=True)
                with gc_col2:
                    st.image(gradcam_path, caption=t("gradcam_caption"), use_container_width=True)

        # Card 2: Risk Factors Checklist
        if checklist:
            st.markdown(f"""
            <div class="ags-card">
                <div class="ags-eyebrow">{t("risk_factors_eyebrow")}</div>
                <div class="ags-factor-list">
            """, unsafe_allow_html=True)

            for item in checklist:
                is_met = item.get("met", False)
                icon_html = f'<span class="ags-factor-icon-checked">☑</span>' if is_met else f'<span class="ags-factor-icon-unchecked">☐</span>'
                factor_txt = item.get("factor", "")
                detail_txt = item.get("detail", "")
                
                st.markdown(f"""
                <div class="ags-factor-item">
                    {icon_html}
                    <div>
                        <div style="font-weight: {'600' if is_met else '400'}; color: {INK if is_met else INK_SECONDARY};">
                            {factor_txt}
                        </div>
                        {f'<div class="ags-caption">{detail_txt}</div>' if detail_txt else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

        # Card 3: Advisory Subsections
        immediate_action = advisory.get("ipm_measures", ["Remove and destroy infected lower leaves"])[0]
        st.markdown(f"""
        <div class="ags-card ags-card-terracotta">
            <div class="ags-eyebrow" style="color: {ACCENT_TERRACOTTA};">{t("immediate_action_eyebrow")}</div>
            <div style="font-size: 0.95rem; font-weight: 600; color: {INK}; margin-top: 0.25rem;">
                — {immediate_action}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="ags-card">
            <div class="ags-eyebrow">{t("field_advisory_eyebrow")}</div>
        """, unsafe_allow_html=True)

        # Symptoms
        symptoms = advisory.get("symptoms", [])
        if symptoms:
            st.markdown(f"<div style='font-size: 0.85rem; font-weight: 600; color: #2F5233; margin-top: 0.5rem;'>{t('diag_symptoms')}</div>", unsafe_allow_html=True)
            for sym in (symptoms if isinstance(symptoms, list) else [symptoms]):
                st.markdown(f"<div class='ags-caption' style='color: {INK};'>• {sym}</div>", unsafe_allow_html=True)

        # Prevention
        prevention = advisory.get("prevention", [])
        if prevention:
            st.markdown(f"<div style='font-size: 0.85rem; font-weight: 600; color: #2F5233; margin-top: 0.75rem;'>{t('long_term_prevention')}</div>", unsafe_allow_html=True)
            for prev in (prevention if isinstance(prevention, list) else [prevention]):
                st.markdown(f"<div class='ags-caption' style='color: {INK};'>• {prev}</div>", unsafe_allow_html=True)

        # Safe Input Guidance
        safe_inputs = advisory.get("safe_input_guidance", [])
        if safe_inputs:
            st.markdown(f"<div style='font-size: 0.85rem; font-weight: 600; color: #2F5233; margin-top: 0.75rem;'>{t('safe_chemical_guidance')}</div>", unsafe_allow_html=True)
            for inp in (safe_inputs if isinstance(safe_inputs, list) else [safe_inputs]):
                st.markdown(f"<div class='ags-caption' style='color: {INK};'>• {inp}</div>", unsafe_allow_html=True)

        # When to contact expert
        expert_contact = advisory.get("when_to_contact_expert", "")
        if expert_contact:
            st.markdown(f"""
            <div style="background-color: #F7F3EC; border-radius: 4px; padding: 0.75rem; margin-top: 1rem; border: 1px solid #DCD5C7;">
                <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: {ACCENT_TERRACOTTA};">{t("contact_expert_header")}</div>
                <div class="ags-caption" style="color: {INK}; margin-top: 0.2rem;">{expert_contact}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    if st.button(t("scan_another_btn"), key="btn_reset_diag"):
        if "diagnosis_result" in st.session_state:
            del st.session_state["diagnosis_result"]
        st.rerun()
