"""Create an untrained model file for pipeline smoke tests.

This does NOT replace Colab training — predictions will be meaningless until
you run ml/train.py on the real PlantVillage dataset. Use this only to verify
predict() and Grad-CAM wiring before the trained .keras file is available.

Usage:
    python ml/create_minimal_model.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.labels import DISEASE_CLASSES, INPUT_SIZE

MODELS_DIR = Path(__file__).resolve().parent / "models"


def main() -> None:
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    base = MobileNetV2(
        input_shape=(INPUT_SIZE, INPUT_SIZE, 3),
        include_top=False,
        weights=None,
    )
    inputs = layers.Input(shape=(INPUT_SIZE, INPUT_SIZE, 3))
    x = layers.Lambda(preprocess_input)(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    outputs = layers.Dense(len(DISEASE_CLASSES), activation="softmax")(x)
    model = models.Model(inputs, outputs)

    model_path = MODELS_DIR / "tomato_mobilenetv2.keras"
    model.save(model_path)

    last_conv = None
    for layer in reversed(base.layers):
        shape = getattr(layer, "output_shape", None)
        if shape is not None and len(shape) == 4:
            last_conv = layer.name
            break

    metadata = {
        "class_labels": DISEASE_CLASSES,
        "last_conv_layer_name": last_conv,
        "input_size": INPUT_SIZE,
        "val_accuracy": 0.0,
        "note": "Untrained smoke-test model — replace after Colab training.",
    }
    metadata_path = MODELS_DIR / "model_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print(f"Saved untrained model to {model_path}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
