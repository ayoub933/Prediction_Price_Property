import re

def extract_price(price_string):
    if price_string is None:
        return None
    prix = re.sub(r"[^\d]", "", price_string)
    return float(prix) if prix else None