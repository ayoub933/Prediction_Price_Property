import pandas as pd
import numpy as np
from database.connection import get_connection

# On charge les données de la db pour soit rent soit sales selon l'argument passé en paramètre
def load_data(listing_type):
    connexion = get_connection()
    q = """
    SELECT
    id, title, address, price::float, surface,
    rooms, property_type, latitude, longitude, scraped_at, source
    FROM properties
    WHERE price IS NOT NULL AND listing_type = %s
    """
    df = pd.read_sql(q, connexion, params=[listing_type])
    connexion.close()
    return df

# On nettoie le fichier (m2), impute des données (surface/rooms/geo) et certaines features comme la ville
def basic_clean(df):
    df = df.copy()

    # surface en m2 (la surface est en sqft, conversion directe)
    if "surface_sqm" not in df or df["surface_sqm"].isna().all():
        df["surface_sqm"] = np.where(df["surface"].notna(), df["surface"] * 0.092903, np.nan)

    # on extirpe de la colonne adress la ville (ex : x rue y, paris (75000) -> paris)
    addr = df["address"].fillna("")
    parts = addr.str.split(",", expand=True)
    df["city"] = (
        parts[1].fillna("").str.replace(r"\(.*\)", "", regex=True).str.strip()
    )
    # on est au canada donc il y'a la province (ex : '2157 Denby Drive Basement, Pickering (Brock Ridge), ON, L1X 2A8, CA' ON pour ontario) 
    df["province"] = (
        parts[2].fillna("").str.replace(r"\(.*\)", "", regex=True).str.strip()
    )

    # pour aider le modele, on met une colonne has_surface, 1 si l'annonce a une surface, 0 sinon
    df["has_surface"] = df["surface_sqm"].notna().astype(int)

    # on prend la médiane la plus précise possible, si elle n'existe pas (g1) on passe a une médiane moins précise etc jusqu'a g5 qui est globale
    g1 = df.groupby(["city","property_type","rooms"], dropna=False)["surface_sqm"].transform("median") # médiane par (ville, type de bien, nb de pièces)
    g2 = df.groupby(["province","property_type","rooms"], dropna=False)["surface_sqm"].transform("median") # médiane par province, type de bien, nb de pièces
    g3 = df.groupby(["city","property_type"], dropna=False)["surface_sqm"].transform("median") # ville, type de bien
    g4 = df.groupby(["property_type","rooms"], dropna=False)["surface_sqm"].transform("median") # type de bien, nb de pièce
    g5 = df["surface_sqm"].median() # globale

    # s'il manque la surface d'un appartement à toronto qui contient 2 pièce, on va voir la médiane d'autres exemples les plus proche(g1-g5) pour imputer avec précision
    df["surface_sqm"] = (
        df["surface_sqm"]
        .fillna(g1).fillna(g2).fillna(g3).fillna(g4).fillna(g5)
    )

    # rooms: médiane par city, sinon globale
    city_rooms_med = df.groupby("city", dropna=False)["rooms"].transform("median")
    df["rooms"] = df["rooms"].fillna(city_rooms_med).fillna(df["rooms"].median())

    # geo: médiane par city si dispo (sinon on garde NA et on dropera)
    city_lat_med = df.groupby("city", dropna=False)["latitude"].transform("median")
    city_lon_med = df.groupby("city", dropna=False)["longitude"].transform("median")
    df["latitude"]  = df["latitude"].fillna(city_lat_med)
    df["longitude"] = df["longitude"].fillna(city_lon_med)

    # bornes raisonnables (valeurs aberrantes supprimées)
    df = df[(df["surface_sqm"] > 10) & (df["surface_sqm"] < 2000)]
    df = df[(df["rooms"] >= 0) & (df["rooms"] <= 10)]

    # rares lat/lon encore NA -> on enlève
    df = df[df["latitude"].notna() & df["longitude"].notna()]

    # anti-outliers prix (1–99%) si assez de données
    if len(df) >= 100:
        lo, hi = np.percentile(df["price"], [1, 99])
        df = df[(df["price"] >= lo) & (df["price"] <= hi)]

    # top 30 des villes pour limiter l'overfitting (limiter la dimensionalité)
    top_cities = df["city"].value_counts().head(30).index
    df["city_30"] = np.where(df["city"].isin(top_cities), df["city"], "Other")

    return df

 #train = plus anciennes, test = plus récentes, plus réaliste pour les prix du marché
def time_split(df, test_frac=0.2):
    df = df.sort_values("scraped_at").reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    return df.iloc[:cut], df.iloc[cut:]
