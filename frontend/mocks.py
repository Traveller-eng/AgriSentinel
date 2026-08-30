"""
Frontend Mocks Suite for AgriSentinel
Provides high-fidelity mock implementations of M1's ML and M2's Backend functions.
Allows instant end-to-end development, testing, and UI demonstration when backend packages are unavailable.
"""

import os
import uuid
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image, ImageDraw, ImageFilter

# --- DOMAIN CONSTANTS ---
DISEASE_CLASSES = [
    "Early Blight",
    "Late Blight",
    "Leaf Mold",
    "Septoria Leaf Spot",
    "Bacterial Spot",
    "Yellow Leaf Curl Virus",
    "Healthy"
]

GROWTH_STAGES = [
    "Seedling",
    "Vegetative",
    "Flowering",
    "Fruiting",
    "Harvest"
]

# Hardcoded Maharashtra Village Coordinates (Wardha District & surroundings)
MAHARASHTRA_VILLAGES = {
    "Wardha (HQ)": (20.7453, 78.6022, "Wardha"),
    "Hinganghat": (20.5524, 78.8358, "Wardha"),
    "Arvi": (20.9840, 78.2323, "Wardha"),
    "Seloo": (20.8358, 78.7061, "Wardha"),
    "Deoli": (20.6621, 78.4795, "Wardha"),
    "Samudrapur": (20.5894, 79.0305, "Wardha"),
    "Karanja Ghadge": (21.1963, 78.5878, "Wardha"),
    "Ashti": (21.2057, 78.1818, "Wardha"),
    "Nagpur Rural": (21.1458, 79.0882, "Nagpur"),
    "Ralegaon": (20.4217, 78.5133, "Yavatmal")
}

# In-memory store for session persistence during demo
_REPORTS_STORE: List[Dict[str, Any]] = [
    {
        "report_id": 101,
        "farm_id": "MH-NGP-4412",
        "farmer_name": "Ramesh Patil",
        "village": "Wardha",
        "district": "Wardha",
        "lat": 20.7453,
        "lon": 78.6022,
        "crop": "Tomato",
        "growth_stage": "Flowering",
        "predicted_disease": "Early Blight",
        "confidence": 0.87,
        "risk_level": "Moderate Risk",
        "status": "pending",
        "created_at": "2026-08-29 09:15",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": ""
    },
    {
        "report_id": 102,
        "farm_id": "MH-NGP-3891",
        "farmer_name": "Sunita Deshmukh",
        "village": "Hinganghat",
        "district": "Wardha",
        "lat": 20.5524,
        "lon": 78.8358,
        "crop": "Tomato",
        "growth_stage": "Fruiting",
        "predicted_disease": "Late Blight",
        "confidence": 0.94,
        "risk_level": "High Risk",
        "status": "confirmed",
        "created_at": "2026-08-29 10:40",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": "Immediate copper fungicide spray advised."
    },
    {
        "report_id": 103,
        "farm_id": "MH-NGP-5104",
        "farmer_name": "Vijay Sharma",
        "village": "Wardha",
        "district": "Wardha",
        "lat": 20.7510,
        "lon": 78.5980,
        "crop": "Tomato",
        "growth_stage": "Vegetative",
        "predicted_disease": "Leaf Mold",
        "confidence": 0.81,
        "risk_level": "Moderate Risk",
        "status": "pending",
        "created_at": "2026-08-28 14:20",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": ""
    },
    {
        "report_id": 104,
        "farm_id": "MH-NGP-2277",
        "farmer_name": "Priya Bhosale",
        "village": "Arvi",
        "district": "Wardha",
        "lat": 20.9840,
        "lon": 78.2323,
        "crop": "Tomato",
        "growth_stage": "Fruiting",
        "predicted_disease": "Late Blight",
        "confidence": 0.91,
        "risk_level": "High Risk",
        "status": "confirmed",
        "created_at": "2026-08-28 16:50",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": "Field boundary quarantined."
    },
    {
        "report_id": 105,
        "farm_id": "MH-NGP-6655",
        "farmer_name": "Mohan Yadav",
        "village": "Seloo",
        "district": "Wardha",
        "lat": 20.8358,
        "lon": 78.7061,
        "crop": "Tomato",
        "growth_stage": "Flowering",
        "predicted_disease": "Septoria Leaf Spot",
        "confidence": 0.78,
        "risk_level": "Low Risk",
        "status": "rejected",
        "created_at": "2026-08-27 11:10",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": "Physical mechanical injury rather than fungal infection."
    },
    {
        "report_id": 106,
        "farm_id": "MH-NGP-7812",
        "farmer_name": "Kavita Tekam",
        "village": "Deoli",
        "district": "Wardha",
        "lat": 20.6621,
        "lon": 78.4795,
        "crop": "Tomato",
        "growth_stage": "Seedling",
        "predicted_disease": "Bacterial Spot",
        "confidence": 0.85,
        "risk_level": "Moderate Risk",
        "status": "pending",
        "created_at": "2026-08-27 08:30",
        "image_path": None,
        "gradcam_path": None,
        "expert_notes": ""
    }
]

_TRAP_STORE: List[Dict[str, Any]] = []


# --- ML MODULE MOCKS (M1) ---

def predict(image_path: str) -> Dict[str, Any]:
    """
    Mock ML prediction function.
    Analyzes leaf photo and returns predicted disease and confidence (0.0 - 1.0).
    """
    # Deterministic yet realistic output
    disease = "Early Blight"
    conf = 0.87
    return {
        "predicted_disease": disease,
        "confidence": conf
    }


def generate_gradcam(image_path: str, predicted_disease: str) -> Optional[str]:
    """
    Mock Grad-CAM generation function.
    Creates a visual attention heatmap on the uploaded leaf image and saves it.
    """
    try:
        out_dir = Path("outputs")
        out_dir.mkdir(parents=True, exist_ok=True)
        gradcam_filename = f"gradcam_{uuid.uuid4().hex[:8]}.png"
        gradcam_path = str(out_dir / gradcam_filename)

        if image_path and os.path.exists(image_path):
            base_img = Image.open(image_path).convert("RGBA")
            # Create synthetic attention heatmap
            w, h = base_img.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            # Center attention ellipse
            cx, cy = w // 2, h // 2
            rx, ry = w // 3, h // 3
            draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(181, 101, 29, 120))
            draw.ellipse([cx - rx // 2, cy - ry // 2, cx + rx // 2, cy + ry // 2], fill=(162, 62, 43, 160))
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=15))
            blended = Image.alpha_composite(base_img, overlay)
            blended.convert("RGB").save(gradcam_path)
            return gradcam_path
        return None
    except Exception:
        return None


# --- BACKEND DB OPERATIONS MOCKS (M2) ---

def insert_report(
    farm_id: str,
    image_path: str,
    crop: str,
    growth_stage: str,
    predicted_disease: str,
    confidence: float,
    lat: float,
    lon: float,
    district: str,
    gradcam_path: Optional[str] = None
) -> int:
    """Insert a new diagnosis report and return the new report_id."""
    new_id = len(_REPORTS_STORE) + 101
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Infer village from lat/lon or default
    village_name = "Wardha"
    for v_name, (v_lat, v_lon, v_dist) in MAHARASHTRA_VILLAGES.items():
        if abs(v_lat - lat) < 0.05 and abs(v_lon - lon) < 0.05:
            village_name = v_name.split(" ")[0]
            break

    risk_level = "Moderate Risk"
    if "Late" in predicted_disease:
        risk_level = "High Risk"
    elif "Healthy" in predicted_disease:
        risk_level = "Low Risk"

    report_record = {
        "report_id": new_id,
        "farm_id": farm_id or f"MH-NGP-{new_id}",
        "farmer_name": "Field Farmer",
        "village": village_name,
        "district": district or "Wardha",
        "lat": lat,
        "lon": lon,
        "crop": crop or "Tomato",
        "growth_stage": growth_stage or "Flowering",
        "predicted_disease": predicted_disease,
        "confidence": confidence,
        "risk_level": risk_level,
        "status": "pending",
        "created_at": now_str,
        "image_path": image_path,
        "gradcam_path": gradcam_path,
        "expert_notes": ""
    }
    _REPORTS_STORE.insert(0, report_record)
    return new_id


def evaluate_and_update_risk(report_id: int) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Mock risk evaluation combining weather heuristics and epidemiological factors.
    Returns (risk_level, checklist).
    """
    # Find report
    rep = next((r for r in _REPORTS_STORE if r["report_id"] == report_id), None)
    disease = rep["predicted_disease"] if rep else "Early Blight"

    if disease == "Healthy":
        return "Low Risk", []

    level = "Moderate Risk"
    if "Late" in disease:
        level = "High Risk"

    checklist = [
        {"factor": "Humidity > 80% (past 3 days)", "met": True, "detail": "Average relative humidity 84.2%"},
        {"factor": "Temperature 24–30°C", "met": True, "detail": "Current micro-climate temperature 27.5°C"},
        {"factor": "Recent rainfall recorded", "met": True, "detail": "14.5 mm cumulative precipitation in past 48h"},
        {"factor": "Dense canopy observed", "met": False, "detail": "Standard row spacing maintained"},
        {"factor": "Previous season infection", "met": False, "detail": "No prior blight outbreak logged for plot"}
    ]

    if rep:
        rep["risk_level"] = level

    return level, checklist


def get_reports(sort_by: str = 'risk', status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve list of reports with optional status filtering and risk sorting."""
    reports = list(_REPORTS_STORE)
    if status_filter and status_filter.lower() != "all":
        reports = [r for r in reports if r["status"].lower() == status_filter.lower()]

    if sort_by == 'risk':
        risk_order = {"High Risk": 0, "HIGH": 0, "Moderate Risk": 1, "MEDIUM": 1, "Low Risk": 2, "LOW": 2}
        reports.sort(key=lambda x: risk_order.get(x.get("risk_level", "LOW"), 3))
    return reports


def update_report_status(report_id: int, new_status: str, expert_notes: str = "") -> bool:
    """Update report status ('confirmed', 'rejected', 'pending') and attach expert notes."""
    for rep in _REPORTS_STORE:
        if rep["report_id"] == report_id:
            rep["status"] = new_status.lower()
            if expert_notes:
                rep["expert_notes"] = expert_notes
            return True
    return False


def insert_trap_observation(
    farm_id: str,
    pest_name: str,
    count: int,
    trap_type: str,
    observed_at: Any,
    village: str,
    district: Optional[str] = "Wardha"
) -> int:
    """Record an insect pheromone or sticky trap observation."""
    new_id = len(_TRAP_STORE) + 1
    _TRAP_STORE.append({
        "trap_id": new_id,
        "farm_id": farm_id,
        "pest_name": pest_name,
        "count": count,
        "trap_type": trap_type,
        "observed_at": str(observed_at),
        "village": village,
        "district": district
    })
    return new_id


def get_reports_filtered(
    disease: Optional[str] = None,
    date_range: Optional[Any] = None,
    district: Optional[str] = None,
    confirmed_only: bool = True
) -> List[Dict[str, Any]]:
    """Query surveillance reports matching multi-criteria filters for the Official Dashboard."""
    results = list(_REPORTS_STORE)
    if confirmed_only:
        results = [r for r in results if r["status"].lower() == "confirmed"]

    if disease and disease != "All" and disease != "All Diseases":
        results = [r for r in results if r["predicted_disease"].lower() == disease.lower()]

    if district and district != "All" and district != "All Districts":
        results = [r for r in results if r["district"].lower() == district.lower()]

    return results


def get_case_counts_by_day(disease: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return 14-day daily case trajectory for trend charting and weekly delta calculation.
    """
    base_date = datetime.date.today() - datetime.timedelta(days=13)
    # Realistic 14-day historical time-series with recent uptick
    counts_seed = [4, 5, 3, 6, 7, 5, 6, 8, 9, 7, 10, 12, 11, 14]
    data = []
    for i, count in enumerate(counts_seed):
        d = base_date + datetime.timedelta(days=i)
        data.append({
            "date": d.strftime("%d %b"),
            "full_date": d.strftime("%Y-%m-%d"),
            "cases": count if not disease or disease in ["All", "All Diseases"] else max(1, count // 2)
        })
    return data
