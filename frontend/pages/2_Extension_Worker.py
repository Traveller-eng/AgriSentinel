"""
AgriSentinel - Extension Worker Portal (Part B)
Case Queue, Triage Actions, Trap Count Monitoring & Field PDF Report Export
"""

import streamlit as st
import os
import sys
import datetime
import logging
from pathlib import Path
from PIL import Image, UnidentifiedImageError

# Configure paths
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
    get_status_color,
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


def _is_valid_image(path: str | None) -> bool:
    """Check if a file path is a valid, openable image.
    
    Returns False if path is None, doesn't exist, or cannot be opened as an image.
    """
    if not path or not os.path.exists(path):
        return False
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except (UnidentifiedImageError, OSError, Exception):
        return False


# --- SWITCHABLE IMPORTS (Real Backend vs Mock Fallback) ---
USE_MOCKS = False

try:
    if USE_MOCKS:
        raise ImportError("Forced mock usage via USE_MOCKS=True")
    from backend.db_ops import (
        get_reports,
        update_report_status,
        insert_trap_observation
    )
    from backend.models import DISEASE_CLASSES, GROWTH_STAGES
except Exception as e:
    logging.info(f"Using frontend.mocks for Extension Worker due to: {e}")
    from mocks import (
        get_reports,
        update_report_status,
        insert_trap_observation,
        DISEASE_CLASSES,
        GROWTH_STAGES,
        MAHARASHTRA_VILLAGES
    )

st.set_page_config(
    page_title="Extension Worker Portal | AgriSentinel",
    page_icon="📋",
    layout="wide"
)

st.markdown(get_global_css(), unsafe_allow_html=True)

# Maharashtra Village list & coordinates (matching 1_Farmer.py)
VILLAGE_COORDINATES = {
    "Wardha (HQ)": {"lat": 20.7453, "lon": 78.6022, "district": "Wardha"},
    "Hinganghat": {"lat": 20.5524, "lon": 78.8358, "district": "Wardha"},
    "Arvi": {"lat": 20.9840, "lon": 78.2323, "district": "Wardha"},
    "Seloo": {"lat": 20.8358, "lon": 78.7061, "district": "Wardha"},
    "Deoli": {"lat": 20.6621, "lon": 78.4795, "district": "Wardha"},
    "Samudrapur": {"lat": 20.5894, "lon": 79.0305, "district": "Wardha"},
    "Karanja Ghadge": {"lat": 21.1963, "lon": 78.5878, "district": "Wardha"},
    "Ashti": {"lat": 21.2057, "lon": 78.1818, "district": "Wardha"},
}
VILLAGE_OPTIONS = list(VILLAGE_COORDINATES.keys())


def export_report_pdf(report: dict, advisory: dict) -> str:
    """
    Generate a formatted field diagnosis report PDF and save to outputs/.
    Uses ReportLab if available, or falls back to structured text report.
    """
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_id = report.get("id", "000")
    pdf_filename = f"AgriSentinel_Field_Report_{report_id}.pdf"
    pdf_path = str(out_dir / pdf_filename)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#2F5233")
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B6558")
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#B5651D"),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#2B2A26")
        )

        elements = []

        # Header
        elements.append(Paragraph("AgriSentinel · Crop Health Field Diagnosis Report", title_style))
        elements.append(Paragraph(f"Wardha District Agricultural Surveillance Network | Generated: {datetime.datetime.now().strftime('%d %b %Y, %H:%M')}", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2F5233"), spaceAfter=12))

        # Case Summary Table
        conf_pct = f"{int(report.get('confidence', 0.85) * 100)}%"
        data_summary = [
            [Paragraph("<b>Report ID:</b>", body_style), Paragraph(str(report.get("id")), body_style), Paragraph("<b>Status:</b>", body_style), Paragraph(str(report.get("status", "pending")).upper(), body_style)],
            [Paragraph("<b>Farm Plot ID:</b>", body_style), Paragraph(str(report.get("farm_id")), body_style), Paragraph("<b>Submission Date:</b>", body_style), Paragraph(str(report.get("created_at")), body_style)],
            [Paragraph("<b>District:</b>", body_style), Paragraph(str(report.get("district", "Wardha")), body_style), Paragraph("<b>Crop:</b>", body_style), Paragraph(str(report.get("crop", "Tomato")), body_style)],
            [Paragraph("<b>Growth Stage:</b>", body_style), Paragraph(str(report.get("growth_stage", "Flowering")), body_style), Paragraph("<b>Diagnosed Disease:</b>", body_style), Paragraph(f"<b>{report.get('predicted_disease')}</b>", body_style)],
            [Paragraph("<b>Confidence:</b>", body_style), Paragraph(conf_pct, body_style), Paragraph("<b>Risk Severity:</b>", body_style), Paragraph(str(report.get("severity", "LOW")), body_style)],
            [Paragraph("<b>Botanical Pathogen:</b>", body_style), Paragraph(advisory.get("scientific_name", "N/A"), body_style), Paragraph("", body_style), Paragraph("", body_style)],
        ]
        t_el = Table(data_summary, colWidths=[110, 150, 110, 150])
        t_el.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FCFAF6")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#DCD5C7")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#EAE4D8")),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_el)
        elements.append(Spacer(1, 12))

        # Expert Notes Section
        expert_notes = report.get("expert_notes") or "No additional field notes attached by extension officer."
        elements.append(Paragraph("Extension Officer Verification Notes", section_heading))
        elements.append(Paragraph(expert_notes, body_style))
        elements.append(Spacer(1, 8))

        # Advisory Sections
        elements.append(Paragraph("Immediate IPM & Management Recommendations", section_heading))
        ipm_measures = advisory.get("ipm_measures", [])
        if isinstance(ipm_measures, list):
            for ipm in ipm_measures:
                elements.append(Paragraph(f"• {ipm}", body_style))
        else:
            elements.append(Paragraph(f"• {ipm_measures}", body_style))

        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Recommended Chemical / Bio-Formulations", section_heading))
        safe_inputs = advisory.get("safe_input_guidance", [])
        if isinstance(safe_inputs, list):
            for s in safe_inputs:
                elements.append(Paragraph(f"• {s}", body_style))
        else:
            elements.append(Paragraph(f"• {safe_inputs}", body_style))

        elements.append(Spacer(1, 14))
        elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#DCD5C7"), spaceAfter=8))
        elements.append(Paragraph("This document is generated for agricultural extension and surveillance monitoring under the AgriSentinel initiative.", subtitle_style))

        doc.build(elements)
        return pdf_path

    except ImportError:
        txt_path = str(out_dir / f"AgriSentinel_Field_Report_{report_id}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"AGRISENTINEL FIELD DIAGNOSIS REPORT #{report_id}\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("="*50 + "\n\n")
            f.write(f"Farm ID: {report.get('farm_id')}\n")
            f.write(f"District: {report.get('district')}\n")
            f.write(f"Crop: {report.get('crop')} | Growth Stage: {report.get('growth_stage')}\n")
            f.write(f"Diagnosed Disease: {report.get('predicted_disease')} (Confidence: {int(report.get('confidence', 0.85)*100)}%)\n")
            f.write(f"Risk Level: {report.get('severity')}\n")
            f.write(f"Status: {report.get('status')}\n")
            f.write(f"Officer Notes: {report.get('expert_notes')}\n\n")
            f.write("IPM MEASURES:\n")
            for m in advisory.get("ipm_measures", []):
                f.write(f" - {m}\n")
            f.write("\nSAFE INPUT GUIDANCE:\n")
            for s in advisory.get("safe_input_guidance", []):
                f.write(f" - {s}\n")
        return txt_path


# --- PAGE HEADER WITH LANGUAGE SELECTOR ---
hdr_col1, hdr_col2 = st.columns([2, 1], gap="medium")
with hdr_col1:
    st.markdown(f"""
    <div>
        <div class="ags-eyebrow">{t("ext_header_eyebrow")}</div>
        <h1 class="ags-h1" style="margin-bottom: 0.25rem;">{t("ext_header_title")}</h1>
        <p class="ags-subtitle" style="margin-bottom: 0;">{t("ext_header_sub")}</p>
    </div>
    """, unsafe_allow_html=True)

with hdr_col2:
    st.markdown("<div style='margin-top: 0.35rem;'></div>", unsafe_allow_html=True)
    render_language_selector(key_prefix="ext")

st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

tab_queue, tab_trap = st.tabs([t("tab_case_queue"), t("tab_record_trap")])

# ==========================================
# TAB 1: CASE QUEUE & ACTION PANEL
# ==========================================
with tab_queue:
    all_reports_raw = get_reports(sort_by='risk', status_filter=None)
    
    count_all = len(all_reports_raw)
    count_pending = sum(1 for r in all_reports_raw if r.get("status") == "pending")
    count_confirmed = sum(1 for r in all_reports_raw if r.get("status") == "confirmed")
    count_rejected = sum(1 for r in all_reports_raw if r.get("status") == "rejected")

    st.markdown(f"""
    <div style="display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap;">
        <span class="ags-caption" style="font-weight: 600; text-transform: uppercase;">{t("filter_status_label")}</span>
        <span class="ags-badge" style="background-color: #2F5233; color: white;">{t("filter_all")} ({count_all})</span>
        <span class="ags-badge" style="background-color: #9A938222; color: #6B6558; border: 1px solid #DCD5C7;">{t("filter_pending")} ({count_pending})</span>
        <span class="ags-badge" style="background-color: #6B8F7122; color: #6B8F71; border: 1px solid #6B8F7155;">{t("filter_confirmed")} ({count_confirmed})</span>
        <span class="ags-badge" style="background-color: #A23E2B22; color: #A23E2B; border: 1px solid #A23E2B55;">{t("filter_rejected")} ({count_rejected})</span>
    </div>
    """, unsafe_allow_html=True)

    # Status filter options mapping
    status_filter_map = {
        t("filter_all"): None,
        t("filter_pending"): "pending",
        t("filter_confirmed"): "confirmed",
        t("filter_rejected"): "rejected"
    }

    col_filter, col_sort = st.columns([1.5, 1])
    with col_filter:
        status_filter_selected = st.selectbox(
            t("filter_status_label"),
            options=list(status_filter_map.keys()),
            index=0,
            label_visibility="collapsed"
        )

    active_filter = status_filter_map.get(status_filter_selected, None)
    reports = get_reports(sort_by='risk', status_filter=active_filter)

    if not reports:
        st.markdown(render_empty_state("📭", t("no_cases_in_queue"), t("no_cases_matching_filter")), unsafe_allow_html=True)
    else:
        col_list, col_detail = st.columns([1.35, 1.15], gap="large")

        with col_list:
            st.markdown(f"<div class='ags-eyebrow'>{t('submitted_cases_eyebrow')}</div>", unsafe_allow_html=True)

            report_options = {}
            for r in reports:
                r_id = r["id"]
                label = f"#{r_id} · {r.get('farm_id')} — {r.get('predicted_disease')} ({r.get('district', 'Wardha')})"
                report_options[r_id] = label

            current_selected_id = st.session_state.get("selected_extension_report_id", reports[0]["id"])
            if current_selected_id not in report_options:
                current_selected_id = reports[0]["id"]

            st.markdown(f"""
            <div style="display: grid; grid-template-columns: 100px 140px 1fr 90px; gap: 0.5rem; padding: 0.5rem 0.75rem; background-color: #EFEBE3; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: {INK_SECONDARY}; text-transform: uppercase;">
                <div>{t("col_farm_id")}</div>
                <div>{t("col_farmer_village")}</div>
                <div>{t("col_disease_conf")}</div>
                <div style="text-align: right;">{t("col_status")}</div>
            </div>
            """, unsafe_allow_html=True)

            for r in reports:
                r_id = r["id"]
                is_selected = (r_id == current_selected_id)
                r_color = get_risk_color(r.get("severity", "LOW"))
                s_color = get_status_color(r.get("status", "pending"))
                conf_val = f"{int(r.get('confidence', 0.85) * 100)}%"

                selected_card_style = f"border: 2px solid {BRAND_GREEN}; background-color: #F8FBF8;" if is_selected else f"border: 1px solid {BORDER}; background-color: {SURFACE};"

                st.markdown(f"""
                <div style="margin-top: 0.5rem; padding: 0.75rem; border-radius: 6px; {selected_card_style}">
                    <div style="display: grid; grid-template-columns: 100px 140px 1fr 90px; gap: 0.5rem; align-items: center;">
                        <div>
                            <div style="font-weight: 700; font-size: 0.875rem; color: {INK};">{r.get('farm_id')}</div>
                            <div class="ags-caption">#{r_id}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.875rem; font-weight: 600; color: {INK};">{r.get('farmer_name', 'Farmer')}</div>
                            <div class="ags-caption">{r.get('district', 'Wardha')}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.875rem; font-weight: 600; color: {INK};">{r.get('predicted_disease')}</div>
                            <div class="ags-caption">{conf_val} · {render_badge(r.get('severity', 'LOW'), r_color)}</div>
                        </div>
                        <div style="text-align: right;">
                            {render_badge(r.get('status', 'pending').capitalize(), s_color)}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"{t('btn_inspect_case')} #{r_id}", key=f"btn_sel_{r_id}", use_container_width=True):
                    st.session_state["selected_extension_report_id"] = r_id
                    st.rerun()

        with col_detail:
            selected_rep = next((r for r in reports if r["id"] == current_selected_id), reports[0])
            sel_advisory = get_advisory(selected_rep.get("predicted_disease"))
            sel_risk_color = get_risk_color(selected_rep.get("severity", "LOW"))
            sel_status_color = get_status_color(selected_rep.get("status", "pending"))

            st.markdown(f"""
            <div class="ags-card" style="border-top: 4px solid {BRAND_GREEN};">
                <div class="ags-eyebrow">{t("case_inspection_eyebrow")}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h2 class="ags-h2" style="font-size: 1.35rem; margin: 0;">Case #{selected_rep['id']} — {selected_rep.get('farm_id')}</h2>
                    {render_badge(selected_rep.get('status', 'pending').upper(), sel_status_color)}
                </div>
                <div class="ags-caption" style="margin-bottom: 1rem;">
                    {t("case_submitted_on")} {selected_rep.get('created_at')} · {selected_rep.get('district', 'Wardha')}
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background-color: #F7F3EC; border-radius: 4px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                <div><strong>{t("grid_crop")}</strong> {selected_rep.get('crop', 'Tomato')}</div>
                <div><strong>{t("grid_growth_stage")}</strong> {selected_rep.get('growth_stage', 'Flowering')}</div>
                <div><strong>{t("grid_predicted")}</strong> {selected_rep.get('predicted_disease')}</div>
                <div><strong>{t("grid_confidence")}</strong> {int(selected_rep.get('confidence', 0.85)*100)}%</div>
                <div><strong>{t("grid_risk_level")}</strong> {render_badge(selected_rep.get('severity', 'LOW'), sel_risk_color)}</div>
            </div>
            """, unsafe_allow_html=True)

            img_path = selected_rep.get("image_path")
            gc_path = selected_rep.get("gradcam_path")
            if _is_valid_image(img_path) or _is_valid_image(gc_path):
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    if _is_valid_image(img_path):
                        st.image(img_path, caption=t("original_sample_caption"), use_container_width=True)
                with col_img2:
                    if _is_valid_image(gc_path):
                        st.image(gc_path, caption=t("gradcam_caption"), use_container_width=True)

            st.markdown(f"<div style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: #6B6558; margin-top: 0.5rem;'>{t('expert_notes_label')}</div>", unsafe_allow_html=True)
            expert_notes_input = st.text_area(
                t("expert_notes_label"),
                value=selected_rep.get("expert_notes", ""),
                placeholder=t("expert_notes_placeholder"),
                label_visibility="collapsed"
            )

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button(t("btn_confirm"), key="btn_confirm_act", use_container_width=True):
                    try:
                        update_report_status(selected_rep["id"], "confirmed", expert_notes_input)
                        st.success(f"Case #{selected_rep['id']} -> CONFIRMED.")
                        st.rerun()
                    except Exception as e_act:
                        logging.error(f"Failed to confirm report: {e_act}")
                        st.error("Could not update case status. Please try again.")

            with btn_col2:
                if st.button(t("btn_reject"), key="btn_reject_act", use_container_width=True):
                    try:
                        update_report_status(selected_rep["id"], "rejected", expert_notes_input)
                        st.warning(f"Case #{selected_rep['id']} -> REJECTED.")
                        st.rerun()
                    except Exception as e_act:
                        logging.error(f"Failed to reject report: {e_act}")
                        st.error("Could not update case status. Please try again.")

            with btn_col3:
                if st.button(t("btn_send_lab"), key="btn_lab_act", use_container_width=True):
                    try:
                        lab_note = f"Sent to lab for verification. Remarks: {expert_notes_input}".strip()
                        update_report_status(selected_rep["id"], "sent_to_lab", lab_note)
                        st.info(f"Case #{selected_rep['id']} flagged for Laboratory Dispatch.")
                        st.rerun()
                    except Exception as e_act:
                        logging.error(f"Failed to flag for lab: {e_act}")
                        st.error("Could not update case status. Please try again.")

            st.markdown("---")

            pdf_path = export_report_pdf(selected_rep, sel_advisory)
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                st.download_button(
                    label=t("download_pdf_btn"),
                    data=pdf_bytes,
                    file_name=Path(pdf_path).name,
                    mime="application/pdf" if pdf_path.endswith(".pdf") else "text/plain",
                    use_container_width=True
                )

            st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# TAB 2: TRAP COUNT MONITORING FORM
# ==========================================
with tab_trap:
    st.markdown(f"""
    <div class="ags-card">
        <div class="ags-eyebrow">{t("trap_entry_eyebrow")}</div>
        <h2 class="ags-h2" style="font-size: 1.35rem; margin-bottom: 0.25rem;">{t("trap_form_title")}</h2>
        <p class="ags-caption" style="margin-bottom: 1.25rem;">
            {t("trap_form_sub")}
        </p>
    """, unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        trap_farm_id = st.text_input(t("farm_id_label"), value="MH-NGP-4412", placeholder="e.g. MH-NGP-XXXX")
        trap_pest_name = st.text_input(t("trap_pest_name_label"), value="Tuta absoluta (Tomato Pinworm)", placeholder="e.g. Whitefly, Fruit Borer")
        trap_count = st.number_input(t("trap_count_label"), min_value=0, value=12, step=1)

    # Trap types mapping
    trap_types_map = {
        t("trap_type_pheromone"): "Pheromone trap",
        t("trap_type_sticky"): "Yellow sticky trap",
        t("trap_type_light"): "Light trap",
        t("trap_type_delta"): "Delta trap",
        t("trap_type_other"): "Other"
    }

    with col_t2:
        trap_type_display = st.selectbox(
            t("trap_type_label"),
            options=list(trap_types_map.keys()),
            index=0
        )
        trap_type_eng = trap_types_map.get(trap_type_display, "Pheromone trap")
        trap_date = st.date_input(t("trap_date_label"), value=datetime.date.today(), max_value=datetime.date.today())
        trap_village = st.selectbox(t("trap_village_label"), options=VILLAGE_OPTIONS, index=0)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(t("trap_submit_btn"), type="primary", use_container_width=True):
        if not trap_farm_id.strip():
            st.error("Farm Plot ID cannot be empty.")
        elif not trap_pest_name.strip():
            st.error("Please specify the target pest or vector name.")
        elif trap_count < 0:
            st.error("Trap count cannot be negative.")
        elif trap_date > datetime.date.today():
            st.error("Observation date cannot be in the future.")
        else:
            try:
                village_data = VILLAGE_COORDINATES[trap_village]
                obs_id = insert_trap_observation(
                    farm_id=trap_farm_id.strip(),
                    pest_name=trap_pest_name.strip(),
                    count=trap_count,
                    trap_type=trap_type_eng,
                    observed_at=trap_date.isoformat(),
                    lat=village_data["lat"],
                    lon=village_data["lon"],
                    district=village_data["district"],
                )
                st.success(f"✓ Observation #{obs_id} successfully recorded for {trap_pest_name} ({trap_count} count) at {trap_village}.")
            except Exception as e_trap:
                logging.error(f"Error submitting trap observation: {e_trap}")
                st.error("Could not record trap observation. Please verify inputs.")
