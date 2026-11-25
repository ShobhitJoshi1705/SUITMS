import pytest
import os
import sys

# Ensure packages are in python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "services", "inference-worker"))

from pipeline.plate_normalizer import PlateNormalizer

def test_clean_text():
    assert PlateNormalizer.clean_text("ka-01 ab 1234") == "KA01AB1234"
    assert PlateNormalizer.clean_text(" DL.03.C.9999 ") == "DL03C9999"
    assert PlateNormalizer.clean_text("") == ""

def test_standard_valid_plates():
    plate, is_valid, conf = PlateNormalizer.normalize("KA01AB1234")
    assert is_valid is True
    assert plate == "KA01AB1234"
    assert conf >= 0.85

    plate, is_valid, conf = PlateNormalizer.normalize("DL03C9876")
    assert is_valid is True
    assert plate == "DL03C9876"

def test_ocr_optical_confusion_repair():
    # '0' in state prefix should become 'O'
    # 'O' in number suffix should become '0'
    raw_noisy = "KA01AB12O4" # Notice 'O' instead of '0'
    plate, is_valid, _ = PlateNormalizer.normalize(raw_noisy)
    assert plate == "KA01AB1204"

    raw_letter_noise = "1RA01AB1234" # '1' -> 'I'
    plate, is_valid, _ = PlateNormalizer.normalize(raw_letter_noise)
    assert plate.startswith("I")

def test_short_or_invalid_plate():
    plate, is_valid, conf = PlateNormalizer.normalize("ABC")
    assert is_valid is False
    assert conf < 0.5
