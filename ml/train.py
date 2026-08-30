"""Fine-tune MobileNetV2 on 5 tomato disease classes.

Designed for Google Colab (free GPU) or local training.

Dataset layout (after download from PlantVillage / Kaggle):
    data/tomato/
        Tomato___Bacterial_spot/
        Tomato___Early_blight/
        Tomato___Late_blight/
        Tomato___Tomato_Yellow_Leaf_Curl_Virus/
        Tomato___healthy/

Colab quick start:
    !pip install tensorflow pillow
    !git clone <your-repo-url> AgriSentinel   # or upload ml/ folder
    # Upload / mount dataset under AgriSentinel/data/tomato/
    !python ml/train.py --data-dir data/tomato --epochs 10

Exports:
    ml/models/tomato_mobilenetv2.keras
    ml/models/model_metadata.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.labels import DISEASE_CLASSES, FOLDER_TO_LABEL, INPUT_SIZE
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "tomato"
MODELS_DIR = Path(__file__).resolve().parent / "models"


def _set_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import tensorflow as tf

        tf.random.set_seed(seed)
    except ImportError:
        pass


def _discover_class_dirs(data_dir: Path) -> dict[str, Path]:
    """Map canonical label → folder path."""
    mapping: dict[str, Path] = {}
    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset directory not found: {data_dir}. "
            "Download PlantVillage tomato classes into data/tomato/."
        )

    for folder in sorted(data_dir.iterdir()):
        if not folder.is_dir():
            continue
        label = FOLDER_TO_LABEL.get(folder.name)
        if label is None:
            # Try case-insensitive match on folder name tail.
            for key, canonical in FOLDER_TO_LABEL.items():
                if key.lower() == folder.name.lower():
                    label = canonical
                    break
        if label and label in DISEASE_CLASSES:
            mapping[label] = folder

    missing = [name for name in DISEASE_CLASSES if name not in mapping]
    if missing:
        raise FileNotFoundError(
            f"Missing class folders for: {missing}. "
            f"Found folders: {[p.name for p in data_dir.iterdir() if p.is_dir()]}"
        )
    return mapping


def _build_datasets(
    class_dirs: dict[str, Path],
    img_size: int,
    batch_size: int,
    val_split: float,
    seed: int,
):
    """Build train/val tf.data datasets from folder paths."""
    import tensorflow as tf

    # image_dataset_from_directory expects subfolder names; we symlink/copy
    # into a temp layout with canonical names for consistent label order.
    staging = MODELS_DIR / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    for label in DISEASE_CLASSES:
        src = class_dirs[label]
        dest = staging / label.replace(" ", "_")
        dest.mkdir(parents=True, exist_ok=True)
        for img_path in src.glob("*"):
            if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
                link = dest / img_path.name
                if not link.exists():
                    try:
                        os.link(img_path, link)
                    except OSError:
                        shutil.copy2(img_path, link)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        staging,
        labels="inferred",
        label_mode="categorical",
        class_names=[name.replace(" ", "_") for name in DISEASE_CLASSES],
        validation_split=val_split,
        subset="training",
        seed=seed,
        image_size=(img_size, img_size),
        batch_size=batch_size,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        staging,
        labels="inferred",
        label_mode="categorical",
        class_names=[name.replace(" ", "_") for name in DISEASE_CLASSES],
        validation_split=val_split,
        subset="validation",
        seed=seed,
        image_size=(img_size, img_size),
        batch_size=batch_size,
    )

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)
    return train_ds, val_ds, staging


def _build_model(num_classes: int, img_size: int, learning_rate: float):
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications.mobilenet_v2 import (
        MobileNetV2,
        preprocess_input,
    )

    base = MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = layers.Input(shape=(img_size, img_size, 3))
    x = layers.Lambda(preprocess_input)(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model, base


def _find_last_conv_in_base(base_model) -> str:
    import tensorflow as tf

    for layer in reversed(base_model.layers):
        shape = getattr(layer, "output_shape", None)
        if shape is not None and len(shape) == 4:
            return layer.name
    raise ValueError("No conv layer found in MobileNetV2 base.")


def train(
    data_dir: Path,
    epochs: int = 10,
    batch_size: int = 32,
    val_split: float = 0.2,
    learning_rate: float = 1e-4,
    fine_tune_epochs: int = 5,
    fine_tune_lr: float = 1e-5,
    seed: int = 42,
) -> dict:
    """Train, fine-tune, evaluate, and export the tomato classifier."""
    import tensorflow as tf

    _set_seed(seed)
    class_dirs = _discover_class_dirs(data_dir)
    train_ds, val_ds, staging = _build_datasets(
        class_dirs, INPUT_SIZE, batch_size, val_split, seed
    )

    model, base = _build_model(len(DISEASE_CLASSES), INPUT_SIZE, learning_rate)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=3,
            restore_best_weights=True,
        ),
    ]

    print("Phase 1: training head (base frozen)...")
    history1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
    )

    print("Phase 2: fine-tuning top layers of MobileNetV2...")
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=fine_tune_lr),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    history2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=fine_tune_epochs,
        callbacks=callbacks,
    )

    _, val_accuracy = model.evaluate(val_ds, verbose=0)
    print(f"Validation accuracy: {val_accuracy * 100:.1f}%")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "tomato_mobilenetv2.keras"
    model.save(model_path)

    last_conv = _find_last_conv_in_base(base)
    metadata = {
        "class_labels": DISEASE_CLASSES,
        "last_conv_layer_name": last_conv,
        "input_size": INPUT_SIZE,
        "val_accuracy": float(val_accuracy),
        "num_classes": len(DISEASE_CLASSES),
    }
    metadata_path = MODELS_DIR / "model_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    if staging.exists():
        shutil.rmtree(staging)

    return {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "val_accuracy": float(val_accuracy),
        "history_epochs": len(history1.history["loss"]) + len(history2.history["loss"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AgriSentinel tomato classifier.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Root folder with 5 tomato class subfolders.",
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--fine-tune-epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = train(
        data_dir=args.data_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        val_split=args.val_split,
        fine_tune_epochs=args.fine_tune_epochs,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
