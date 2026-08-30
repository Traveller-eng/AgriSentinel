"""Smoke tests for the ML inference package."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml.labels import DISEASE_CLASSES, FOLDER_TO_LABEL, LABEL_TO_INDEX
from ml.predict import ModelNotFoundError, load_image, preprocess_image


def test_disease_classes_match_backend():
    backend_labels = [
        "Bacterial Spot",
        "Early Blight",
        "Late Blight",
        "Yellow Leaf Curl Virus",
        "Healthy",
    ]
    assert DISEASE_CLASSES == backend_labels


def test_folder_mapping_covers_all_classes():
    mapped = set(FOLDER_TO_LABEL.values())
    for label in DISEASE_CLASSES:
        assert label in mapped


def test_label_to_index():
    assert LABEL_TO_INDEX["Healthy"] == 4
    assert len(LABEL_TO_INDEX) == 5


def test_load_image_from_temp_png(tmp_path):
    from PIL import Image

    path = tmp_path / "leaf.png"
    Image.new("RGB", (64, 64), color=(0, 128, 0)).save(path)
    img = load_image(path)
    assert img.mode == "RGB"
    assert img.size == (64, 64)


def test_preprocess_image_shape():
    pytest.importorskip("tensorflow")
    from PIL import Image

    img = Image.new("RGB", (100, 80), color=(34, 139, 34))
    batch, resized = preprocess_image(img)
    assert batch.shape == (1, 224, 224, 3)
    assert resized.size == (224, 224)


def test_predict_raises_when_model_missing():
    pytest.importorskip("tensorflow")
    from PIL import Image

    from ml.predict import predict

    img = Image.new("RGB", (224, 224), color=(0, 100, 0))
    with pytest.raises(ModelNotFoundError):
        predict(img, model_path=Path("/nonexistent/model.keras"))
