"""Disease class labels shared between training and inference."""

from __future__ import annotations

# Must match backend/models.py DISEASE_CLASSES exactly (order = model output index).
DISEASE_CLASSES: list[str] = [
    "Bacterial Spot",
    "Early Blight",
    "Late Blight",
    "Yellow Leaf Curl Virus",
    "Healthy",
]

# PlantVillage / Kaggle folder names → canonical label.
FOLDER_TO_LABEL: dict[str, str] = {
    "Tomato___Bacterial_spot": "Bacterial Spot",
    "Tomato___Early_blight": "Early Blight",
    "Tomato___Late_blight": "Late Blight",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Yellow Leaf Curl Virus",
    "Tomato___healthy": "Healthy",
    # Common alternate spellings from renamed datasets.
    "Bacterial_spot": "Bacterial Spot",
    "Early_blight": "Early Blight",
    "Late_blight": "Late Blight",
    "Tomato_Yellow_Leaf_Curl_Virus": "Yellow Leaf Curl Virus",
    "healthy": "Healthy",
}

LABEL_TO_INDEX: dict[str, int] = {
    name: index for index, name in enumerate(DISEASE_CLASSES)
}

INPUT_SIZE = 224
