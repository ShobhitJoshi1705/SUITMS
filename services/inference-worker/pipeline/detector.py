import os
import random
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("suitms.detector")

class TrafficDetector:
    """
    Traffic & Violation Detection Engine.
    Uses YOLOv8 when available, or a deterministic ML simulator fallback
    when weights are not present locally.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("YOLO_MODEL_PATH", r"Dataset\runs\detect\helmet_training\weights\best.pt")
        self.yolo_model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                from ultralytics import YOLO
                logger.info(f"Loading custom YOLOv8 model from {self.model_path}...")
                self.yolo_model = YOLO(self.model_path)
                logger.info("YOLOv8 weights loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load YOLO model: {e}. Running in lightweight robust fallback mode.")
        else:
            logger.info(f"YOLO weights not found at {self.model_path}. Initialized in high-fidelity mock/test mode.")

    def detect_frame(self, frame_np: Optional[np.ndarray] = None, seed_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs object detection on frame.
        Detects: bikes, riders, helmets, no_helmets, number plates.
        """
        if self.yolo_model is not None and frame_np is not None:
            try:
                results = self.yolo_model(frame_np, verbose=False)
                # Parse YOLO results
                boxes = []
                counts = {"bike": 0, "rider": 0, "helmet": 0, "no_helmet": 0, "number_plate": 0}
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = r.names.get(cls_id, "unknown")
                        conf = float(box.conf[0])
                        xyxy = [float(x) for x in box.xyxy[0]]
                        counts[cls_name] = counts.get(cls_name, 0) + 1
                        boxes.append({"class": cls_name, "confidence": conf, "bbox": xyxy})
                
                violations = self.evaluate_rules(counts)
                return {
                    "boxes": boxes,
                    "counts": counts,
                    "violations": violations,
                    "is_fallback": False
                }
            except Exception as e:
                logger.error(f"Inference error with YOLO: {e}, using fallback logic.")

        # Deterministic ML fallback simulator
        rng = random.Random(seed_hint or str(random.random()))
        has_bike = True
        num_riders = rng.choice([1, 2, 3])
        num_helmets = rng.choice([0, 1]) if num_riders == 1 else rng.choice([0, 1, 2])
        num_no_helmets = max(0, num_riders - num_helmets)
        
        counts = {
            "bike": 1 if has_bike else 0,
            "rider": num_riders,
            "helmet": num_helmets,
            "no_helmet": num_no_helmets,
            "number_plate": 1
        }
        
        violations = self.evaluate_rules(counts)
        boxes = [
            {"class": "bike", "confidence": 0.92, "bbox": [100, 200, 400, 600]},
            {"class": "rider", "confidence": 0.88, "bbox": [150, 100, 350, 500]},
            {"class": "number_plate", "confidence": 0.94, "bbox": [220, 520, 320, 570]}
        ]
        if num_helmets > 0:
            boxes.append({"class": "helmet", "confidence": 0.89, "bbox": [180, 80, 260, 150]})
        if num_no_helmets > 0:
            boxes.append({"class": "no_helmet", "confidence": 0.91, "bbox": [180, 80, 260, 150]})
            
        return {
            "boxes": boxes,
            "counts": counts,
            "violations": violations,
            "is_fallback": True
        }

    def evaluate_rules(self, counts: Dict[str, int]) -> List[Dict[str, Any]]:
        """Evaluates traffic violation rules (Helmet, Triple Riding)."""
        reasons = []
        b_count = counts.get("bike", 0)
        nh_count = counts.get("no_helmet", 0)
        r_count = counts.get("rider", 0)
        h_count = counts.get("helmet", 0)
        
        if b_count >= 1:
            # Rule 1: No Helmet
            if nh_count >= 1 or (r_count > 0 and h_count < r_count):
                reasons.append({
                    "type": "NO_HELMET",
                    "description": "Riding motorcycle without mandatory protective helmet",
                    "confidence": 0.92
                })
            # Rule 2: Triple Riding
            if r_count > 2 * b_count:
                reasons.append({
                    "type": "TRIPLE_RIDING",
                    "description": f"Over-capacity carrying: {r_count} riders detected on {b_count} motorcycle",
                    "confidence": 0.95
                })
        return reasons
