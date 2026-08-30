"""
AgriSentinel Design System & UI Utilities
Central source of truth for visual tokens, global CSS injection, and reusable HTML components.
"""

import json
import os
from pathlib import Path

# --- DEFAULT DESIGN TOKENS ---
DEFAULT_TOKENS = {
    "colors": {
        "background": "#F7F3EC",
        "surface": "#FCFAF6",
        "ink": "#2B2A26",
        "ink_secondary": "#6B6558",
        "border": "#DCD5C7",
        "brand_green": "#2F5233",
        "accent_terracotta": "#B5651D",
        "risk_low": "#6B8F71",
        "risk_medium": "#C99A3B",
        "risk_high": "#A23E2B",
        "status_pending": "#9A9382",
        "status_confirmed": "#6B8F71",
        "status_rejected": "#A23E2B",
    },
    "fonts": {
        "heading": "Fraunces",
        "body": "IBM Plex Sans"
    },
    "radius_px": 6,
    "spacing_unit_px": 8
}


def _clean_str(val):
    if isinstance(val, str):
        return val.strip().replace("\n", "").replace("\r", "")
    return val


def _load_tokens():
    """Attempt to load design_tokens.json from potential file paths; fallback to defaults."""
    possible_paths = [
        Path(__file__).parent.parent / "design_reference" / "design_tokens.json",
        Path(__file__).parent / "design_reference" / "design_tokens.json",
        Path("frontend/design_reference/design_tokens.json"),
        Path("design_reference/design_tokens.json"),
    ]

    tokens = DEFAULT_TOKENS.copy()
    for p in possible_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    if "colors" in raw and isinstance(raw["colors"], dict):
                        for k, v in raw["colors"].items():
                            tokens["colors"][k] = _clean_str(v)
                    if "fonts" in raw and isinstance(raw["fonts"], dict):
                        for k, v in raw["fonts"].items():
                            tokens["fonts"][k] = _clean_str(v)
                    if "radius_px" in raw:
                        tokens["radius_px"] = int(raw["radius_px"])
                    if "spacing_unit_px" in raw:
                        tokens["spacing_unit_px"] = int(raw["spacing_unit_px"])
                break
            except Exception:
                pass
    return tokens


TOKENS = _load_tokens()
COLORS = TOKENS["colors"]

# Public Color and Font Constants
BRAND_GREEN = COLORS.get("brand_green", "#2F5233")
ACCENT_TERRACOTTA = COLORS.get("accent_terracotta", "#B5651D")
BG_PAPER = COLORS.get("background", "#F7F3EC")
SURFACE = COLORS.get("surface", "#FCFAF6")
INK = COLORS.get("ink", "#2B2A26")
INK_SECONDARY = COLORS.get("ink_secondary", "#6B6558")
BORDER = COLORS.get("border", "#DCD5C7")

FONT_HEADING = TOKENS["fonts"].get("heading", "Fraunces")
FONT_BODY = TOKENS["fonts"].get("body", "IBM Plex Sans")
RADIUS_PX = TOKENS.get("radius_px", 6)
SPACING_UNIT_PX = TOKENS.get("spacing_unit_px", 8)

RISK_COLORS = {
    "LOW": COLORS.get("risk_low", "#6B8F71"),
    "MEDIUM": COLORS.get("risk_medium", "#C99A3B"),
    "HIGH": COLORS.get("risk_high", "#A23E2B"),
    "Low Risk": COLORS.get("risk_low", "#6B8F71"),
    "Moderate Risk": COLORS.get("risk_medium", "#C99A3B"),
    "High Risk": COLORS.get("risk_high", "#A23E2B"),
    "Low": COLORS.get("risk_low", "#6B8F71"),
    "Moderate": COLORS.get("risk_medium", "#C99A3B"),
    "High": COLORS.get("risk_high", "#A23E2B"),
}

STATUS_COLORS = {
    "pending": COLORS.get("status_pending", "#9A9382"),
    "confirmed": COLORS.get("status_confirmed", "#6B8F71"),
    "rejected": COLORS.get("status_rejected", "#A23E2B"),
    "Pending": COLORS.get("status_pending", "#9A9382"),
    "Confirmed": COLORS.get("status_confirmed", "#6B8F71"),
    "Rejected": COLORS.get("status_rejected", "#A23E2B"),
}


def get_risk_color(level: str) -> str:
    """Retrieve canonical hex color for a given risk level string."""
    if not level:
        return RISK_COLORS["LOW"]
    clean = str(level).strip().upper()
    if "HIGH" in clean:
        return RISK_COLORS["HIGH"]
    if "MED" in clean or "MOD" in clean:
        return RISK_COLORS["MEDIUM"]
    return RISK_COLORS["LOW"]


def get_status_color(status: str) -> str:
    """Retrieve canonical hex color for a given status string."""
    if not status:
        return STATUS_COLORS["pending"]
    clean = str(status).strip().lower()
    if "confirm" in clean:
        return STATUS_COLORS["confirmed"]
    if "reject" in clean:
        return STATUS_COLORS["rejected"]
    return STATUS_COLORS["pending"]


def get_global_css() -> str:
    """
    Generate unified global CSS injected once per page.
    Includes Google Fonts, color tokens, Streamlit widget overrides, and utility classes.
    """
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

/* --- Root & Global Variables --- */
:root {{
    --ags-bg: {BG_PAPER};
    --ags-surface: {SURFACE};
    --ags-ink: {INK};
    --ags-ink-sec: {INK_SECONDARY};
    --ags-border: {BORDER};
    --ags-brand: {BRAND_GREEN};
    --ags-accent: {ACCENT_TERRACOTTA};
    --ags-radius: {RADIUS_PX}px;
}}

/* --- Hide Streamlit Default Chrome --- */
#MainMenu, footer, header, div[data-testid="stDecoration"] {{
    display: none !important;
}}

/* --- Base Body & App Container --- */
.stApp {{
    background-color: var(--ags-bg) !important;
    color: var(--ags-ink) !important;
    font-family: '{FONT_BODY}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}}

/* Main container spacing */
.block-container {{
    max-width: 960px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
}}

/* --- Typography Classes --- */
.ags-eyebrow {{
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ags-ink-sec);
    margin-bottom: 0.25rem;
}}

.ags-h1 {{
    font-family: '{FONT_HEADING}', Georgia, serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--ags-ink);
    line-height: 1.15;
    margin: 0 0 0.5rem 0;
}}

.ags-h2 {{
    font-family: '{FONT_HEADING}', Georgia, serif;
    font-size: 1.65rem;
    font-weight: 600;
    color: var(--ags-ink);
    line-height: 1.25;
    margin: 0 0 0.4rem 0;
}}

.ags-h3 {{
    font-family: '{FONT_HEADING}', Georgia, serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--ags-ink);
    line-height: 1.3;
    margin: 0 0 0.35rem 0;
}}

.ags-subtitle {{
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.95rem;
    color: var(--ags-ink-sec);
    margin: 0 0 1.25rem 0;
    line-height: 1.4;
}}

.ags-body {{
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.925rem;
    color: var(--ags-ink);
    line-height: 1.5;
}}

.ags-caption {{
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.8rem;
    color: var(--ags-ink-sec);
    line-height: 1.4;
}}

/* --- Card & Container Styles --- */
.ags-card {{
    background-color: var(--ags-surface);
    border: 1px solid var(--ags-border);
    border-radius: var(--ags-radius);
    padding: 1.25rem;
    margin-bottom: 1rem;
    transition: border-color 0.15s ease;
}}

.ags-card:hover {{
    border-color: #C0B7A5;
}}

.ags-card-accent {{
    border-left: 4px solid var(--ags-brand);
}}

.ags-card-terracotta {{
    border-left: 4px solid var(--ags-accent);
    background-color: #FDF9F5;
}}

.ags-card-dashed {{
    background-color: var(--ags-surface);
    border: 1.5px dashed var(--ags-border);
    border-radius: var(--ags-radius);
    padding: 2rem 1.5rem;
    text-align: center;
    margin-bottom: 1rem;
}}

/* --- Badge & Pill Components --- */
.ags-badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.65rem;
    border-radius: 4px;
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}}

.ags-crop-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background-color: #EBF2EC;
    color: var(--ags-brand);
    border: 1px solid #C4D9C7;
    border-radius: 4px;
    padding: 0.3rem 0.75rem;
    font-size: 0.825rem;
    font-weight: 600;
    margin-bottom: 1rem;
}}

/* --- Stat Block Card --- */
.ags-stat-card {{
    background-color: var(--ags-surface);
    border: 1px solid var(--ags-border);
    border-radius: var(--ags-radius);
    padding: 1.1rem;
    height: 100%;
    position: relative;
    box-sizing: border-box;
}}

.ags-stat-val {{
    font-family: '{FONT_HEADING}', Georgia, serif;
    font-size: 2.35rem;
    font-weight: 700;
    color: var(--ags-ink);
    line-height: 1.05;
    margin: 0.35rem 0 0.25rem 0;
}}

/* --- Checklists & Factors --- */
.ags-factor-list {{
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.5rem;
}}

.ags-factor-item {{
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    font-size: 0.9rem;
    color: var(--ags-ink);
}}

.ags-factor-icon-checked {{
    color: var(--ags-brand);
    font-weight: 700;
    font-size: 1rem;
    line-height: 1.2;
}}

.ags-factor-icon-unchecked {{
    color: var(--ags-ink-sec);
    opacity: 0.45;
    font-size: 1rem;
    line-height: 1.2;
}}

/* --- Streamlit Native Widget Theming --- */
/* Primary Buttons */
.stButton > button {{
    background-color: var(--ags-brand) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--ags-brand) !important;
    border-radius: var(--ags-radius) !important;
    font-family: '{FONT_BODY}', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}}

.stButton > button:hover {{
    background-color: #244128 !important;
    border-color: #244128 !important;
    color: #FFFFFF !important;
}}

.stButton > button:active {{
    background-color: #1B321E !important;
}}

/* Secondary / Outline Button */
.stButton > button[kind="secondary"] {{
    background-color: var(--ags-surface) !important;
    color: var(--ags-ink) !important;
    border: 1px solid var(--ags-border) !important;
}}

.stButton > button[kind="secondary"]:hover {{
    background-color: #F3EFE7 !important;
    border-color: #C0B7A5 !important;
    color: var(--ags-ink) !important;
}}

/* Form Inputs, Selectboxes, Datepickers */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {{
    background-color: var(--ags-surface) !important;
    color: var(--ags-ink) !important;
    border-color: var(--ags-border) !important;
    border-radius: var(--ags-radius) !important;
    font-family: '{FONT_BODY}', sans-serif !important;
}}

div[data-baseweb="select"]:hover > div,
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: var(--ags-brand) !important;
}}

/* Progress Bar */
.stProgress > div > div > div > div {{
    background-color: var(--ags-accent) !important;
}}

/* Radio Group as Segmented Buttons */
div[data-testid="stRadio"] > div {{
    gap: 0.5rem;
}}

div[data-testid="stRadio"] label {{
    background-color: var(--ags-surface);
    border: 1px solid var(--ags-border);
    border-radius: var(--ags-radius);
    padding: 0.45rem 0.9rem;
    font-family: '{FONT_BODY}', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--ags-ink);
    cursor: pointer;
    transition: all 0.15s ease;
}}

div[data-testid="stRadio"] label:hover {{
    border-color: #C0B7A5;
    background-color: #F7F3EB;
}}

/* Alert / Callouts */
.stAlert {{
    border-radius: var(--ags-radius) !important;
    border: 1px solid var(--ags-border) !important;
    background-color: var(--ags-surface) !important;
}}
</style>
"""


def render_badge(label: str, color: str, bg_tint: str = None) -> str:
    """
    Shared badge component helper.
    Produces clean, pixel-consistent badges for risk, status, and alerts.
    """
    if not bg_tint:
        # Default to a gentle 12% tint background of the main color
        bg_style = f"background-color: {color}1F; border: 1px solid {color}55; color: {color};"
    else:
        bg_style = f"background-color: {bg_tint}; border: 1px solid {color}55; color: {color};"

    return f"""<span class="ags-badge" style="{bg_style}">{label}</span>"""


def render_header(title: str, subtitle: str = None, category: str = None, right_badge_html: str = None) -> str:
    """Produce standardized page and section headers with optional eyebrow and right badge."""
    eyebrow_html = f'<div class="ags-eyebrow">{category}</div>' if category else ""
    sub_html = f'<div class="ags-subtitle">{subtitle}</div>' if subtitle else ""
    badge_html = f'<div style="margin-left: auto;">{right_badge_html}</div>' if right_badge_html else ""

    return f"""
    <div style="display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.25rem;">
        <div>
            {eyebrow_html}
            <h1 class="ags-h1">{title}</h1>
            {sub_html}
        </div>
        {badge_html}
    </div>
    """


def render_stat_card(label: str, value: str, subtext: str = None, delta: str = None, border_accent: str = None) -> str:
    """Produce clean KPI metric card matching the Figma design reference."""
    accent_style = f"border-left: 4px solid {border_accent};" if border_accent else ""
    subtext_html = f'<div class="ags-caption" style="margin-top: 0.2rem;">{subtext}</div>' if subtext else ""
    delta_html = f'<div style="font-size: 0.8rem; font-weight: 600; color: {border_accent or INK_SECONDARY}; margin-top: 0.45rem;">{delta}</div>' if delta else ""

    return f"""
    <div class="ags-stat-card" style="{accent_style}">
        <div class="ags-eyebrow" style="margin-bottom: 0.15rem;">{label}</div>
        <div class="ags-stat-val">{value}</div>
        {subtext_html}
        {delta_html}
    </div>
    """


def render_card(content_html: str, border_color: str = None, bg_color: str = None) -> str:
    """Wraps HTML content inside an AgriSentinel surface card."""
    border_style = f"border-color: {border_color};" if border_color else ""
    bg_style = f"background-color: {bg_color};" if bg_color else ""
    return f"""
    <div class="ags-card" style="{border_style} {bg_style}">
        {content_html}
    </div>
    """


def render_empty_state(icon: str, title: str, description: str) -> str:
    """Render friendly on-brand empty state."""
    return f"""
    <div class="ags-card-dashed">
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-family: '{FONT_HEADING}', serif; font-size: 1.15rem; font-weight: 600; color: {INK}; margin-bottom: 0.35rem;">{title}</div>
        <div style="font-size: 0.875rem; color: {INK_SECONDARY}; max-width: 420px; margin: 0 auto;">{description}</div>
    </div>
    """
