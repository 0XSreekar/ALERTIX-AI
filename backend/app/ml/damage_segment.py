"""Damage assessment via pretrained DeepLabV3 ResNet-50 (torchvision optional)."""
from __future__ import annotations

import io
import logging

log = logging.getLogger(__name__)

try:
    import torch
    import torchvision.transforms as T
    from PIL import Image
    from torchvision.models.segmentation import DeepLabV3_ResNet50_Weights, deeplabv3_resnet50

    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

# PASCAL VOC 2012 class labels (21 classes including background)
PASCAL_CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat", "bottle",
    "bus", "car", "cat", "chair", "cow", "diningtable", "dog",
    "horse", "motorbike", "person", "pottedplant", "sheep", "sofa",
    "train", "tvmonitor",
]

_model = None


def _load_model():
    global _model
    if _model is None:
        weights = DeepLabV3_ResNet50_Weights.DEFAULT
        _model = deeplabv3_resnet50(weights=weights)
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
            log.info("DeepLabV3 loaded on GPU")
        else:
            log.info("DeepLabV3 loaded on CPU")
    return _model


def segment_image(image_bytes: bytes) -> dict:
    """Run pretrained DeepLabV3 on uploaded image bytes.

    Returns dict with class pixel percentages, dominant class,
    and a simple damage confidence score. Falls back gracefully
    if torch/torchvision are not installed.
    """
    if not _HAS_TORCH:
        return {
            "classes": {},
            "dominant_class": None,
            "damage_confidence": None,
            "model_version": None,
            "message": "ML dependencies not installed (pip install -e '.[ml]')",
        }

    try:
        model = _load_model()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        preprocess = T.Compose([
            T.Resize((520, 520)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        input_tensor = preprocess(img).unsqueeze(0)
        if torch.cuda.is_available():
            input_tensor = input_tensor.cuda()

        with torch.no_grad():
            output = model(input_tensor)["out"][0]

        pred = output.argmax(0).cpu().numpy()
        total = pred.size

        class_pct: dict[str, float] = {}
        for idx, name in enumerate(PASCAL_CLASSES):
            count = int((pred == idx).sum())
            if count > 0:
                class_pct[name] = round(count / total * 100, 2)

        class_pct = dict(sorted(class_pct.items(), key=lambda x: -x[1]))
        dominant = next(iter(class_pct), None)

        # Heuristic damage confidence: elevated vehicle/person presence
        # in relation to total scene suggests populated disaster area
        person_pct = class_pct.get("person", 0.0)
        vehicle_pct = sum(class_pct.get(c, 0.0) for c in ["car", "bus", "boat", "aeroplane"])
        damage_conf = min(1.0, round((person_pct * 0.01) + (vehicle_pct * 0.02), 3))

        return {
            "classes": class_pct,
            "dominant_class": dominant,
            "damage_confidence": damage_conf,
            "model_version": "deeplabv3_resnet50_pascal_voc_coco",
        }
    except Exception as exc:
        log.exception("DeepLabV3 inference failed: %s", exc)
        return {
            "classes": {},
            "dominant_class": None,
            "damage_confidence": None,
            "model_version": None,
            "message": f"Inference error: {exc}",
        }
