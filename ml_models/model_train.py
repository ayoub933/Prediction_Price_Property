import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from ml_models.features import load_data, basic_clean, time_split
from database.connection import get_connection
import psycopg2.extras

# On retourne le df numérique propre que la fonction basic_clean (features.py) a d'abord nettoyer
def make_base(df):
    rooms_safe = df["rooms"].astype(float).clip(lower=0.5)  # évite /0 pour la colonne surf_per_room
    return pd.DataFrame({
        "surface_sqm": df["surface_sqm"].astype(float),
        "has_surface": df["has_surface"].astype(int), # 1 s'il y"a une surface dispo, 0 sinon
        "rooms": df["rooms"].astype(float),
        "latitude": df["latitude"].astype(float),
        "longitude": df["longitude"].astype(float),
        "is_appt": (df["property_type"] == "appartement").astype(int), # 1 si c'est un appart, 0 sinon
        "surf_per_room": (df["surface_sqm"].astype(float) / rooms_safe).fillna(0.0), # surface de l'appart/maison sur le nombre de pièces
    }).fillna(0)

# Ecrire les predictions dans la base approprié (price_prediction, détail dans le fichier migrations.sql)
def upsert_predictions(ids, preds, confs):
    connexion = get_connection()
    cursor = connexion.cursor()
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_price_predictions_property
        ON price_predictions(property_id);
        """)
    # On insère les valeurs passées en paramètre, si property_id existe déjà dans la table (ON CONFLICT), on met à jour les nouvelles valeurs
    sql = """
      INSERT INTO price_predictions(property_id, predicted_price, confidence_score)
      VALUES (%s, %s, %s)
      ON CONFLICT (property_id) DO UPDATE
        SET predicted_price = EXCLUDED.predicted_price,
            confidence_score = EXCLUDED.confidence_score,
            created_at = NOW();
    """
    rows = [( int(i), float(p), float(c) ) for i, p, c in zip(ids, preds, confs)]
    psycopg2.extras.execute_batch(cursor, sql, rows, page_size=1000)
    connexion.commit()
    cursor.close()
    connexion.close()

def train_and_write(listing_type):
    # debug taille
    df0 = load_data(listing_type)
    df  = basic_clean(df0)
    print(f"[{listing_type}] rows raw = {len(df0)} -> après nettoyage = {len(df)}")
    
    # 80% seront entrainée sur les annonces les plus anciennes, 20% sont testés sur les annonces les plus récentes 
    train, test = time_split(df, test_frac=0.2)

    # base numériques
    base_tr = make_base(train)
    base_te = make_base(test)

    # One-Hot Encoding (dummies) utilisé ici pour rendre les catégories en variable binaire
    cats_tr = pd.get_dummies(train[["province", "city_30"]].fillna("NA"))
    cats_te = pd.get_dummies(test[["province", "city_30"]].fillna("NA"))
    cats_te = cats_te.reindex(columns=cats_tr.columns, fill_value=0) # meme colonne dans train et test

    # Matrices finales X(info donnée au modèle) / y(ce qu'il doit prédire (prix)) pour l'algo ML
    Xtr = pd.concat([base_tr, cats_tr], axis=1)
    Xte = pd.concat([base_te, cats_te], axis=1)
    ytr, yte = train["price"].astype(float), test["price"].astype(float) # prix réel (cible)

    # cible en log (meilleure stabilité sur sale car il y'a de très gros prix)
    ytr_log = np.log1p(ytr)

    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=18,
        min_samples_leaf=5,
        max_features="sqrt",
        n_jobs=-1,
        random_state=42
    )
    # on entraîne le modèle
    rf.fit(Xtr, ytr_log)
    pred_log = rf.predict(Xte)
    pred = np.expm1(pred_log) # résultats retransformés en prix réels

    mae  = mean_absolute_error(yte, pred)
    mape = np.mean(np.abs((yte - pred) / np.clip(yte, 0.00000001, None))) * 100
    print(f"[{listing_type}] n_train={len(train)} n_test={len(test)} && MAE={mae:,.0f} && MAPE={mape:,.1f}%")

    # ré-entraîner sur l'ensemble du dataset
    base_all = make_base(df)
    cats_all = pd.get_dummies(df[["province", "city_30"]].fillna("NA"))
    X_all = pd.concat([base_all, cats_all], axis=1)

    rf.fit(X_all, np.log1p(df["price"].astype(float))) # réduit l'effet des énormes prix

    # Moyenne des prédictions de chaque arbre (sur l'échelle $) + incertitude = std/mean
    Xa = X_all.values  # array numpy, sans feature
    all_log = np.column_stack([est.predict(Xa) for est in rf.estimators_])  # prédictions de chaque arbre individuellement
    all_pred = np.expm1(all_log) # retour à l’échelle

    preds_all = all_pred.mean(axis=1) # moyenne arithmétique des prédictions en euros sur tous les arbres (ex : [1980,2020,2050,...] -> 2015 de moyenne sur 200 arbres)
    rel_std = all_pred.std(axis=1) / (preds_all + 0.00000001) # écart type (0.00000001 pour éviter de diviser par 0)
    confs = 1.0 / (1.0 + rel_std) # entre 0 et 1 (plus haut = plus confiant)

    # on remplie la db avec les valeurs de confiance, l'id et la prediction
    upsert_predictions(df["id"].values, preds_all, confs)
    print(f"[{listing_type}] {len(df)} prédictions écrites dans la db.")


if __name__ == "__main__":
    train_and_write("rent")
    train_and_write("sale")
