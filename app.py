"""AgriSentinel Streamlit MVP app."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db_ops import (
    evaluate_and_update_risk,
    get_case_counts_by_day,
    get_reports,
    get_reports_filtered,
    insert_report,
    insert_trap_observation,
    update_report_status,
)
from init_db import init_db
from models import DISEASE_CLASSES, GROWTH_STAGES

try:
    from ml.predict import ModelNotFoundError, predict_with_gradcam
except Exception:
    ModelNotFoundError = FileNotFoundError
    predict_with_gradcam = None

UPLOAD_DIR = ROOT / "uploads"
GRADCAM_DIR = UPLOAD_DIR / "gradcam"
KB_PATH = ROOT / "data" / "knowledge_base.json"
DEFAULT_LOCATION = {"lat": 19.1176, "lon": 73.9654, "district": "Pune"}
RISK_COLORS = {"HIGH": "#d64545", "MEDIUM": "#d6902f", "LOW": "#2f9e67", None: "#77808a"}


st.set_page_config(
    page_title="AgriSentinel",
    page_icon="AS",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f7faf7; }
        [data-testid="stSidebar"] { background: #12352f; }
        [data-testid="stSidebar"] * { color: #f4fff7 !important; }
        .block-container { padding-top: 1.6rem; }
        .metric-tile {
            border: 1px solid #dfe8df;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
        }
        .risk-high { color: #b42318; font-weight: 700; }
        .risk-medium { color: #9a5b00; font-weight: 700; }
        .risk-low { color: #067647; font-weight: 700; }
        .small-muted { color: #667085; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_knowledge_base() -> dict:
    with KB_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def risk_class(level: str | None) -> str:
    return {
        "HIGH": "risk-high",
        "MEDIUM": "risk-medium",
        "LOW": "risk-low",
    }.get(level or "", "")


def demo_predict(image_bytes: bytes) -> tuple[str, float, str | None]:
    digest = hashlib.sha256(image_bytes).digest()
    disease = DISEASE_CLASSES[digest[0] % len(DISEASE_CLASSES)]
    confidence = 0.64 + ((digest[1] % 31) / 100)
    return disease, min(confidence, 0.94), None


def run_prediction(image_bytes: bytes) -> tuple[str, float, str | None, bool]:
    if predict_with_gradcam is None:
        disease, confidence, gradcam = demo_predict(image_bytes)
        return disease, confidence, gradcam, True
    try:
        disease, confidence, gradcam = predict_with_gradcam(image_bytes, output_dir=GRADCAM_DIR)
        return disease, confidence, gradcam, False
    except Exception:
        disease, confidence, gradcam = demo_predict(image_bytes)
        return disease, confidence, gradcam, True


def save_upload(uploaded_file) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
    target = UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(uploaded_file.getvalue()).hexdigest()[:8]}{suffix}"
    target.write_bytes(uploaded_file.getvalue())
    return str(target)


def advisory_panel(disease: str, kb: dict) -> None:
    item = kb.get(disease)
    if not item:
        st.info("No advisory text is available for this class yet.")
        return
    st.subheader(item["display_name"])
    tabs = st.tabs(["Symptoms", "Conditions", "Prevention", "IPM", "Safe inputs", "Expert referral"])
    keys = [
        "symptoms",
        "favorable_conditions",
        "prevention",
        "ipm_measures",
        "safe_input_guidance",
        "when_to_contact_expert",
    ]
    for tab, key in zip(tabs, keys):
        with tab:
            for line in item[key]:
                st.write(f"- {line}")


def render_checklist(checklist: list[dict]) -> None:
    for item in checklist:
        marker = "PASS" if item.get("passed") else "WATCH"
        st.write(f"**{marker} - {item.get('factor')}**: {item.get('detail')}")


def farmer_page(kb: dict) -> None:
    st.title("AgriSentinel Farmer Diagnosis")
    st.caption("Tomato crop-health detection with weather-aware risk scoring and advisory support.")

    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        st.subheader("Submit crop photo")
        with st.form("farmer_form"):
            farm_id = st.text_input("Farm ID", value="FARM-DEMO-001")
            growth_stage = st.selectbox("Growth stage", GROWTH_STAGES, index=2)
            uploaded = st.file_uploader("Tomato leaf image", type=["jpg", "jpeg", "png"])
            c1, c2, c3 = st.columns(3)
            lat = c1.number_input("Latitude", value=DEFAULT_LOCATION["lat"], format="%.6f")
            lon = c2.number_input("Longitude", value=DEFAULT_LOCATION["lon"], format="%.6f")
            district = c3.text_input("District", value=DEFAULT_LOCATION["district"])
            submit = st.form_submit_button("Run diagnosis", use_container_width=True)

        if uploaded is not None:
            st.image(uploaded, caption="Uploaded leaf image", use_container_width=True)

    with right:
        if submit:
            if uploaded is None:
                st.warning("Upload a tomato leaf image before running diagnosis.")
                return
            with st.spinner("Analyzing image, weather and nearby confirmed reports..."):
                image_bytes = uploaded.getvalue()
                disease, confidence, gradcam_path, is_demo = run_prediction(image_bytes)
                image_path = save_upload(uploaded)
                report_id = insert_report(
                    farm_id=farm_id,
                    image_path=image_path,
                    crop="Tomato",
                    growth_stage=growth_stage,
                    predicted_disease=disease,
                    confidence=confidence,
                    lat=lat,
                    lon=lon,
                    district=district,
                    gradcam_path=gradcam_path,
                )
                level, checklist = evaluate_and_update_risk(report_id)
            if is_demo:
                st.warning("Demo fallback prediction is active because the trained .keras model is not present.")
            st.success(f"Report #{report_id} submitted")
            m1, m2, m3 = st.columns(3)
            m1.metric("Diagnosis", disease)
            m2.metric("Confidence", f"{confidence * 100:.0f}%")
            m3.markdown(f"<div class='{risk_class(level)}'>Risk: {level}</div>", unsafe_allow_html=True)
            st.progress(min(max(confidence, 0.0), 1.0))
            if gradcam_path and Path(gradcam_path).exists():
                st.image(gradcam_path, caption="Grad-CAM evidence overlay", use_container_width=True)
            st.subheader("Risk factors")
            render_checklist(checklist)
            advisory_panel(disease, kb)
        else:
            st.info("Fill the form and run diagnosis to generate a report, risk checklist, and advisory.")


def extension_page() -> None:
    st.title("Extension Worker Review")
    st.caption("Prioritize farmer reports, validate cases, and log pest-trap observations.")
    status = st.selectbox("Queue status", ["pending", "sent_to_lab", "confirmed", "rejected", "All"], index=0)
    rows = get_reports(sort_by="risk", status_filter=None if status == "All" else status)

    if not rows:
        st.info("No reports found. Use the Farmer page or run seed_demo_data.py.")
    else:
        df = pd.DataFrame(rows)
        show_cols = ["id", "farm_id", "predicted_disease", "confidence", "severity", "status", "district", "growth_stage", "created_at"]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

        report_ids = [int(row["id"]) for row in rows]
        selected = st.selectbox("Open report", report_ids)
        report = next(row for row in rows if int(row["id"]) == int(selected))
        c1, c2 = st.columns([0.45, 0.55], gap="large")
        with c1:
            image_path = report.get("image_path")
            if image_path and Path(image_path).exists() and Path(image_path).suffix.lower() in [".jpg", ".jpeg", ".png"]:
                st.image(image_path, caption=f"Report #{selected}", use_container_width=True)
            st.metric("Risk", report.get("severity") or "Not scored")
            st.metric("Confidence", f"{float(report.get('confidence') or 0) * 100:.0f}%")
        with c2:
            st.write(f"**Disease:** {report['predicted_disease']}")
            st.write(f"**Farm:** {report['farm_id']} | **District:** {report['district']}")
            notes = st.text_area("Expert notes", value=report.get("expert_notes") or "", height=100)
            b1, b2, b3 = st.columns(3)
            if b1.button("Confirm", use_container_width=True):
                update_report_status(selected, "confirmed", notes or "Confirmed by extension worker.")
                st.rerun()
            if b2.button("Reject", use_container_width=True):
                update_report_status(selected, "rejected", notes or "Rejected after review.")
                st.rerun()
            if b3.button("Send to lab", use_container_width=True):
                update_report_status(selected, "sent_to_lab", notes or "Referred for lab validation.")
                st.rerun()

    st.divider()
    st.subheader("Trap-count entry")
    with st.form("trap_form"):
        c1, c2, c3 = st.columns(3)
        farm_id = c1.text_input("Farm ID", value="FARM-DEMO-001", key="trap_farm")
        pest = c2.selectbox("Pest", ["Whitefly", "Fruit borer", "Aphid", "Leaf miner"])
        count = c3.number_input("Count", min_value=0, step=1, value=8)
        c4, c5, c6 = st.columns(3)
        trap_type = c4.selectbox("Trap type", ["Yellow sticky trap", "Pheromone trap", "Light trap"])
        observed_at = c5.date_input("Observed at", value=date.today())
        district = c6.text_input("District", value=DEFAULT_LOCATION["district"], key="trap_district")
        c7, c8 = st.columns(2)
        lat = c7.number_input("Trap latitude", value=DEFAULT_LOCATION["lat"], format="%.6f")
        lon = c8.number_input("Trap longitude", value=DEFAULT_LOCATION["lon"], format="%.6f")
        submitted = st.form_submit_button("Save trap observation")
    if submitted:
        trap_id = insert_trap_observation(farm_id, pest, count, trap_type, observed_at.isoformat(), lat, lon, district)
        st.success(f"Trap observation #{trap_id} saved")


def official_page() -> None:
    st.title("Official Surveillance Dashboard")
    st.caption("Confirmed reports are shown as simulated/demo surveillance points until real field validation starts.")

    all_reports = get_reports(sort_by="date")
    districts = sorted({row["district"] for row in all_reports})
    f1, f2, f3 = st.columns(3)
    disease = f1.selectbox("Disease", ["All"] + DISEASE_CLASSES)
    district = f2.selectbox("District", ["All"] + districts)
    days = f3.slider("Lookback days", 1, 30, 21)
    start = (date.today() - timedelta(days=days)).isoformat()
    end = date.today().isoformat()

    rows = get_reports_filtered(
        disease=None if disease == "All" else disease,
        district=None if district == "All" else district,
        date_range=(start, end),
        confirmed_only=True,
    )
    if rows:
        df = pd.DataFrame(rows)
        df["color"] = df["severity"].map(RISK_COLORS).fillna("#77808a")
        st.map(df, latitude="lat", longitude="lon", color="color", size=80, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Confirmed cases", len(df))
        c2.metric("High risk", int((df["severity"] == "HIGH").sum()))
        c3.metric("Districts", df["district"].nunique())
        st.dataframe(df[["id", "predicted_disease", "severity", "district", "created_at"]], use_container_width=True, hide_index=True)
    else:
        st.info("No confirmed reports match the current filters. Run seed_demo_data.py if this is a fresh database.")

    trend = pd.DataFrame(get_case_counts_by_day(None if disease == "All" else disease))
    if not trend.empty:
        st.subheader("Case trend")
        st.line_chart(trend, x="date", y="count", use_container_width=True)


def main() -> None:
    init_db()
    inject_css()
    kb = load_knowledge_base()
    st.sidebar.title("AgriSentinel")
    st.sidebar.caption("AI crop-health surveillance MVP")
    page = st.sidebar.radio("View", ["Farmer", "Extension Worker", "Official"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.write("Scope: Tomato only")
    st.sidebar.write("Data: live submissions + disclosed simulated reports")

    if page == "Farmer":
        farmer_page(kb)
    elif page == "Extension Worker":
        extension_page()
    else:
        official_page()


if __name__ == "__main__":
    main()
