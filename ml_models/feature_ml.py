import re
import pandas as pd
from database.connection import get_connection
from ml_models.model_train import trad_list

def extract_property_type(title):
    if not title:
        return "unknown"
    
    title_lower = title.lower()

    # Studio
    if re.search(r"\bstudio\b", title_lower):
        return "studio"

    # 1 bedroom
    if re.search(r"\b(1\s*br|1\s*bed(room)?)\b", title_lower):
        return "1br"

    # 2 à 3 chambres
    match = re.search(r"\b([2-3])\s*(br|bed(rooms?)?)\b", title_lower)
    if match:
        return f"{match.group(1)}br"
    
    return "unknown"

import re

def extract_qualitative_features(title):
    if not title:
        return ["unknown"]
    
    title_lower = title.lower()
    features = []
    
    # Spacious
    if re.search(r"\bspacious\b", title_lower):
        features.append("spacious")
    
    # Bright
    if re.search(r"\bbright\b", title_lower):
        features.append("bright")
    
    # Furnished
    if re.search(r"\bfurnished\b", title_lower):
        features.append("furnished")
    
    # Roof deck
    if re.search(r"\broof\s*deck\b", title_lower):
        features.append("roof_deck")
    
    # Elevator
    if re.search(r"\belevator\b", title_lower):
        features.append("elevator")
    
    # Laundry
    if re.search(r"\blaundry\b", title_lower):
        features.append("laundry")
    
    return features if features else ["unknown"]


connexion = get_connection()
query = "SELECT * FROM properties"
df = pd.read_sql(query, connexion)
connexion.close()

df["property_type_extracted"] = df["title"].apply(extract_property_type)
df["qualitative_features"] = df["title"].apply(extract_qualitative_features)
df.to_csv("properties_ml.csv", index=False)