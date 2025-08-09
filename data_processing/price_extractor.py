import re

def extract_price(price_string):
    if price_string is None:
        return None
    prix = re.sub(r"[^\d]", "", price_string)
    return float(prix) if prix else None


print(extract_price('€1 100'))
print(extract_price('€760'))  
print(extract_price(None))
print(extract_price('€'))
print(extract_price('£2 500 410'))
print(extract_price('$ '))
print(extract_price('1$'))