"""Grad-CAM heatmap overlay for model explainability."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _resolve_conv_layer(model: Any, last_conv_layer_name: str | None) -> Any:
    """Return the Keras layer object used for Grad-CAM."""
    import tensorflow as tf

    if last_conv_layer_name:
        try:
            return model.get_layer(last_conv_layer_name)
        except ValueError:
            pass
        for layer in model.layers:
            if isinstance(layer, tf.keras.Model):
                try:
                    return layer.get_layer(last_conv_layer_name)
                except ValueError:
                    continue

    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.Model):
            for sub in reversed(layer.layers):
                shape = getattr(sub, "output_shape", None)
                if shape is not None and len(shape) == 4:
                    return sub
        shape = getattr(layer, "output_shape", None)
        if shape is not None and len(shape) == 4:
            return layer

    raise ValueError("Could not find a convolutional layer for Grad-CAM.")


def generate_gradcam_overlay(
    model: Any,
    batch: np.ndarray,
    display_image: Image.Image,
    class_index: int,
    last_conv_layer_name: str | None = None,
    alpha: float = 0.45,
) -> Image.Image:
    """Build a Grad-CAM overlay on top of the display image.

    Parameters:
        model: Loaded Keras model.
        batch: Preprocessed input batch (1, H, W, 3).
        display_image: Resized RGB PIL image matching the model input.
        class_index: Target class index for the heatmap.
        last_conv_layer_name: Conv layer name saved during training; auto-detected if None.
        alpha: Blend weight for the heatmap (0 = original only, 1 = heatmap only).

    Returns:
        PIL Image with heatmap blended over the leaf photo.
    """
    import tensorflow as tf

    conv_layer = _resolve_conv_layer(model, last_conv_layer_name)
    grad_model = tf.keras.models.Model(
        inputs=model.input,
        outputs=[conv_layer.output, model.output],
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(batch)
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    if grads is None:
        raise ValueError(f"No gradients for conv layer {conv_layer.name!r}.")

    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(tf.multiply(pooled_grads, conv_outputs), axis=-1)
    heatmap = tf.maximum(heatmap, 0)
    heatmap /= tf.reduce_max(heatmap) + 1e-8
    heatmap = heatmap.numpy()

    heatmap_img = Image.fromarray(np.uint8(255 * heatmap)).resize(
        display_image.size,
        Image.Resampling.BILINEAR,
    )
    heatmap_rgb = np.array(heatmap_img.convert("RGB"), dtype=np.float32)

    # Simple red-yellow colormap: low=blue-ish gray, high=red.
    colored = np.zeros_like(heatmap_rgb)
    intensity = np.array(heatmap_img, dtype=np.float32) / 255.0
    colored[..., 0] = 255 * intensity
    colored[..., 1] = 128 * intensity

    base = np.array(display_image.convert("RGB"), dtype=np.float32)
    blended = (1.0 - alpha) * base + alpha * colored
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    return Image.fromarray(blended)


def save_overlay(overlay: Image.Image, output_dir: str | Path) -> Path:
    """Save overlay PNG and return its path."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"gradcam_{stamp}_{uuid.uuid4().hex[:8]}.png"
    path = directory / filename
    overlay.save(path, format="PNG")
    return path
