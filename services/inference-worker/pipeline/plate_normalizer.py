import os
import re
from typing import Tuple, Optional

class PlateNormalizer:
    """
    Normalizes raw OCR license plate detections into standardized formats.
    Handles common OCR optical character confusions:
      - State code & district series (Letters expected): '0'->'O', '1'->'I', '8'->'B', '5'->'S'
      - Registration digits (Numbers expected): 'O'->'0', 'I'->'1', 'B'->'8', 'S'->'5', 'Z'->'2', 'G'->'6'
    """
    
    # Valid Indian State/UT two-letter prefixes
    VALID_STATE_CODES = {
        "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
        "HR", "HP", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
        "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"
    }

    CHAR_TO_NUM = {
        'O': '0', 'D': '0', 'Q': '0',
        'I': '1', 'L': '1', 'T': '1',
        'Z': '2',
        'E': '3',
        'A': '4',
        'S': '5',
        'G': '6', 'b': '6',
        'B': '8',
    }

    NUM_TO_CHAR = {
        '0': 'O',
        '1': 'I',
        '2': 'Z',
        '3': 'E',
        '4': 'A',
        '5': 'S',
        '6': 'G',
        '8': 'B',
    }

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """Removes spaces, punctuation, special symbols, and converts to uppercase."""
        if not raw_text:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()

    @classmethod
    def normalize(cls, raw_text: str) -> Tuple[str, bool, float]:
        """
        Normalizes raw text to standard format (e.g. KA01AB1234 or DL03C9876).
        Returns: (normalized_plate, is_valid_format, confidence_modifier)
        """
        cleaned = cls.clean_text(raw_text)
        if len(cleaned) < 6:
            return cleaned, False, 0.2

        chars = list(cleaned)

        # 1. First two characters: State Code (must be letters)
        if len(chars) >= 2:
            chars[0] = cls.NUM_TO_CHAR.get(chars[0], chars[0])
            chars[1] = cls.NUM_TO_CHAR.get(chars[1], chars[1])

        # 2. Next 1 or 2 characters: District Code (must be digits)
        # Search for first transition to letters
        district_end = 2
        while district_end < min(len(chars), 4) and (chars[district_end].isdigit() or chars[district_end] in cls.CHAR_TO_NUM):
            chars[district_end] = cls.CHAR_TO_NUM.get(chars[district_end], chars[district_end])
            district_end += 1

        # 3. Last 4 characters: Serial Registration Number (must be digits)
        if len(chars) >= 4:
            for i in range(len(chars) - 4, len(chars)):
                chars[i] = cls.CHAR_TO_NUM.get(chars[i], chars[i])

        # 4. Middle characters: Series (letters)
        for i in range(district_end, max(district_end, len(chars) - 4)):
            chars[i] = cls.NUM_TO_CHAR.get(chars[i], chars[i])

        candidate = "".join(chars)

        # Regex matching standard: 2 letters, 1-2 digits, 1-3 letters, 4 digits
        standard_pattern = r"^([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{4})$"
        match = re.match(standard_pattern, candidate)
        
        if match:
            state = match.group(1)
            is_recognized_state = state in cls.VALID_STATE_CODES
            confidence_mod = 1.0 if is_recognized_state else 0.85
            return candidate, True, confidence_mod
            
        # Fallback lenient regex: minimum 2 letters, numbers, etc.
        lenient_pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z0-9]{4,6}$"
        if re.match(lenient_pattern, candidate):
            return candidate, True, 0.75

        return candidate, False, 0.4
