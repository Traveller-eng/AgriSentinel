"""
Knowledge Base Lookup Utility
Loads knowledge_base.json once and provides structured disease advisories.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

_KB_CACHE: Optional[Dict[str, Any]] = None


def _load_knowledge_base() -> Dict[str, Any]:
    """Load and cache the knowledge base dictionary from available locations."""
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE

    search_paths = [
        Path(__file__).parent.parent.parent / "knowledge_base.json",
        Path(__file__).parent.parent / "knowledge_base.json",
        Path("knowledge_base.json"),
        Path("frontend/knowledge_base.json"),
    ]

    for path in search_paths:
        if path.exists() and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _KB_CACHE = json.load(f)
                    return _KB_CACHE
            except Exception:
                pass

    _KB_CACHE = {
        "Early Blight": {
            "scientific_name": "Alternaria solani",
            "symptoms": [
                "Concentric dark brown rings on older lower leaves",
                "Yellow halos surrounding necrotic spots",
                "Premature lower leaf drop"
            ],
            "prevention": [
                "Practice 2-3 year crop rotation away from solanaceous crops",
                "Avoid overhead irrigation; use drip irrigation",
                "Ensure proper plant spacing for canopy ventilation"
            ],
            "ipm_measures": [
                "Prune and destroy infected lower leaves",
                "Apply bio-fungicide Trichoderma viride @ 5g/L",
                "Spray neem seed kernel extract (NSKE 5%)"
            ],
            "safe_input_guidance": [
                "Spray Mancozeb 75% WP @ 2.5g/L or Chlorothalonil 75% WP @ 2g/L",
                "Observe 7-10 days pre-harvest waiting interval"
            ],
            "when_to_contact_expert": "Contact KVK or extension officer if more than 20% foliage is affected or lesions appear on stems."
        },
        "Healthy": {
            "scientific_name": "Solanum lycopersicum",
            "symptoms": ["Normal green foliage with no disease lesions"],
            "prevention": ["Continue regular scouting and balanced fertilization"],
            "ipm_measures": ["Deploy pheromone monitoring traps"],
            "safe_input_guidance": ["No chemical fungicides required"],
            "when_to_contact_expert": "Continue standard routine field monitoring."
        }
    }
    return _KB_CACHE


def get_advisory(disease_name: str) -> Dict[str, Any]:
    """
    Retrieve structured agronomic advisory for a given disease name.
    Performs case-insensitive matching and fallback normalization.
    """
    kb = _load_knowledge_base()
    if not disease_name:
        return kb.get("Healthy", {})

    if disease_name in kb:
        return kb[disease_name]

    norm_name = str(disease_name).strip().lower()
    for key, value in kb.items():
        if key.lower() == norm_name or key.lower() in norm_name or norm_name in key.lower():
            return value

    return {
        "scientific_name": disease_name,
        "symptoms": [
            f"Foliar irregularities consistent with {disease_name}",
            "Leaf spotting or discoloration observed on upper/lower surfaces"
        ],
        "prevention": [
            "Maintain clean cultivation and sanitize field tools",
            "Avoid excessive overhead moisture on crop foliage",
            "Implement recommended crop rotation"
        ],
        "ipm_measures": [
            "Isolate and remove affected foliage to reduce pathogen spread",
            "Spray biological agents or neem-based formulations"
        ],
        "safe_input_guidance": [
            "Consult local package of practices before applying chemical controls",
            "Follow prescribed dilution rates and safety withholding periods"
        ],
        "when_to_contact_expert": f"Consult your village extension officer for a confirmed laboratory diagnosis of {disease_name}."
    }
