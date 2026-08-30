"""Load image, run MobileNetV2 inference, return disease label and confidence."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from ml.labels import DISEASE_CLASSES, INPUT_SIZE

logger = logging.getLogger(__name__)

_ML_DIR = Path(__file__).resolve().parent
MODELS_DIR = _ML_DIR / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "tomato_mobilenetv2.keras"
DEFAULT_METADATA_PATH = MODELS_DIR / "model_metadata.json"


class ModelNotFoundError(FileNotFoundError):
    """Raised when the trained .keras model file is missing."""


def _resolve_model_path(model_path: str | Path | None) -> Path:
    path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
    if not path.is_file():
        raise ModelNotFoundError(
            f"Model not found at {path}. "
            "Train in Colab with ml/train.py and copy tomato_mobilenetv2.keras "
            "into ml/models/."
        )
    return path


def _load_metadata(metadata_path: Path | None = None) -> dict[str, Any]:
    path = metadata_path or DEFAULT_METADATA_PATH
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        labels = data.get("class_labels", DISEASE_CLASSES)
        return {
            "class_labels": list(labels),
            "last_conv_layer_name": data.get("last_conv_layer_name"),
            "input_size": int(data.get("input_size", INPUT_SIZE)),
        }
    logger.warning("Metadata missing at %s; using default class order.", path)
    return {
        "class_labels": list(DISEASE_CLASSES),
        "last_conv_layer_name": None,
        "input_size": INPUT_SIZE,
    }


@lru_cache(maxsize=1)
def _load_model_cached(model_path_str: str) -> Any:
    """Load the Keras model once per process."""
    import tensorflow as tf

    tf.get_logger().setLevel("ERROR")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    return tf.keras.models.load_model(model_path_str)


def get_model_bundle(model_path: str | Path | None = None) -> dict[str, Any]:
    """Return model, labels, and Grad-CAM layer name for inference."""
    path = _resolve_model_path(model_path)
    metadata = _load_metadata()
    model = _load_model_cached(str(path.resolve()))
    return {
        "model": model,
        "model_path": path,
        "class_labels": metadata["class_labels"],
        "last_conv_layer_name": metadata["last_conv_layer_name"],
        "input_size": metadata["input_size"],
    }


def load_image(image: str | Path | bytes | Image.Image) -> Image.Image:
    """Open an image from path, bytes, or PIL and return RGB."""
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if isinstance(image, (str, Path)):
        return Image.open(image).convert("RGB")
    if isinstance(image, (bytes, bytearray)):
        return Image.open(BytesIO(image)).convert("RGB")
    raise TypeError(f"Unsupported image type: {type(image)!r}")


def preprocess_image(
    image: str | Path | bytes | Image.Image,
    input_size: int = INPUT_SIZE,
) -> tuple[np.ndarray, Image.Image]:
    """Resize and apply MobileNetV2 preprocessing.

    Returns:
        A batch of shape (1, H, W, 3) and the resized RGB PIL image.
    """
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    pil = load_image(image)
    resized = pil.resize((input_size, input_size), Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32)
    arr = preprocess_input(arr)
    batch = np.expand_dims(arr, axis=0)
    return batch, resized


def predict(
    image: str | Path | bytes | Image.Image,
    model_path: str | Path | None = None,
) -> tuple[str, float]:
    """Classify a tomato leaf image.

    Parameters:
        image: File path, raw bytes, or PIL Image.
        model_path: Optional override for the .keras model file.

    Returns:
        ``(predicted_disease, confidence)`` where disease is one of
        ``DISEASE_CLASSES`` and confidence is 0.0–1.0.

    Raises:
        ModelNotFoundError: If the model file does not exist.
        ValueError: If the model output shape does not match class labels.
    """
    bundle = get_model_bundle(model_path)
    model = bundle["model"]
    labels: list[str] = bundle["class_labels"]
    input_size: int = bundle["input_size"]

    batch, _ = preprocess_image(image, input_size=input_size)
    probs = model.predict(batch, verbose=0)[0]

    if len(probs) != len(labels):
        raise ValueError(
            f"Model outputs {len(probs)} classes but metadata lists {len(labels)}."
        )

    index = int(np.argmax(probs))
    confidence = float(probs[index])
    return labels[index], confidence


def predict_with_gradcam(
    image: str | Path | bytes | Image.Image,
    output_dir: str | Path | None = None,
    model_path: str | Path | None = None,
) -> tuple[str, float, str | None]:
    """Run prediction and save a Grad-CAM overlay image.

    Returns:
        ``(predicted_disease, confidence, gradcam_path)``.
        ``gradcam_path`` is None if Grad-CAM generation fails.
    """
    from ml.gradcam import generate_gradcam_overlay, save_overlay

    bundle = get_model_bundle(model_path)
    model = bundle["model"]
    labels: list[str] = bundle["class_labels"]
    input_size: int = bundle["input_size"]
    last_conv = bundle["last_conv_layer_name"]

    batch, resized = preprocess_image(image, input_size=input_size)
    probs = model.predict(batch, verbose=0)[0]
    index = int(np.argmax(probs))
    confidence = float(probs[index])
    disease = labels[index]

    gradcam_path: str | None = None
    try:
        overlay = generate_gradcam_overlay(
            model=model,
            batch=batch,
            display_image=resized,
            class_index=index,
            last_conv_layer_name=last_conv,
        )
        out_dir = Path(output_dir) if output_dir else MODELS_DIR.parent / "outputs" / "gradcam"
        gradcam_path = str(save_overlay(overlay, out_dir))
    except Exception:
        logger.exception("Grad-CAM generation failed; returning prediction only.")

    return disease, confidence, gradcam_path
