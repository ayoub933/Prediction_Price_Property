import re

def extract_price(price_string):
    if price_string is None:
        return None
    # Accepte int/float/Decimal/etc.
    if not isinstance(price_string, str):
        price_string = str(price_string)
    # Garde uniquement les chiffres
    prix = re.sub(r"[^\d]", "", price_string)
    return float(prix) if prix else None
