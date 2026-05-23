import re


def is_valid_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return True
    if len(digits) == 10:
        return True
    return False
