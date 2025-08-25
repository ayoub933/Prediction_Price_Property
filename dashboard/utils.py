import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import plotly.express as px
import numpy as np
import pandas as pd
from database.connection import get_connection
import streamlit as st

# --- DATA ---
@st.cache_data()
def load_properties():
    with get_connection() as conn:
        q = """
        SELECT id, title, address, price::float AS price, rooms, property_type, latitude, longitude,
               listing_type, scraped_at, url, surface::float AS surface
        FROM properties
        """
        return pd.read_sql(q, conn)

# Renvoie un dataframe réunissant les données scrappés et les prédictions de l'algo avec l'autre table
def load_properties_with_predictions():
    with get_connection() as conn:
        q = """
        SELECT p.id, p.title, p.address, p.price::float AS price, p.rooms, p.property_type, p.latitude, p.longitude,
               p.listing_type, p.scraped_at, p.url, p.surface::float AS surface,
            pr.predicted_price::float,
            pr.confidence_score::float,
            pr.created_at AS prediction_date
        FROM properties p
        JOIN price_predictions pr
            ON p.id = pr.property_id;
        """
        df = pd.read_sql(q, conn)
    return df

# On filtre par type, prix, chambres et surface (si dispo)
def apply_filters(df, selected_types, min_price, max_price, rooms_range=None, surface_range=None):
    f = df.copy()
    # Type
    if selected_types and set(selected_types) != {"sale", "rent"}:
        f = f[f["listing_type"].isin(selected_types)]
        
    # Prix
    f = f[(f["price"] >= float(min_price)) & (f["price"] <= float(max_price))]

    # Chambres
    if rooms_range and "rooms" in f.columns:
        rmin, rmax = rooms_range
        f = f[(f["rooms"] >= rmin) & (f["rooms"] <= rmax)]

    # Surface
    if surface_range and "surface" in f.columns:
        smin, smax = surface_range
        f = f[(f["surface"] >= smin) & (f["surface"] <= smax)]

    return f

# KPI
def kpi(df):
    n = len(df)
    if n == 0 or "price" not in df:
        return 0, 0.0, 0.0
    avg = float(df["price"].mean())
    med = float(df["price"].median())
    return n, avg, med

# Sidebar
def sidebar_filters(df):
    st.sidebar.header("Filtres")
    st.sidebar.subheader("Type d'annonce")
    sale_selected = st.sidebar.checkbox("Sale", value=True)
    rent_selected = st.sidebar.checkbox("Rent", value=True)

    selected_types = []
    if sale_selected:
        selected_types.append("sale")
    if rent_selected:
        selected_types.append("rent")
    if not selected_types:
        selected_types = ["sale", "rent"]

    # Prix
    st.sidebar.subheader("Gamme de prix")
    pmin = int(df["price"].min())
    pmax = int(df["price"].max())

    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_price = st.number_input("Prix min", value=pmin, format="%d")
    with col2:
        max_price = st.number_input("Prix max", value=pmax, format="%d")

    # Chambres
    st.sidebar.subheader("Nombre de chambres")
    if "rooms" in df:
        rmin = int(df["rooms"].min())
        rmax = int(df["rooms"].max())
    else:
        rmin, rmax = 0, 11
    rooms_min, rooms_max = st.sidebar.slider("Plage de chambres", min_value=rmin, max_value=rmax, value=(rmin, rmax))

    # Surface en m2
    st.sidebar.subheader("Surface (m²)")
    if "surface" in df:
        smin = int(df["surface"].min())
        smax = int(df["surface"].max())
    else:
        smin, smax = 0, 300
    surface_min, surface_max = st.sidebar.slider("Plage de surface (appuyer flèche du haut et bas pour ajuster précisement)", min_value=smin, max_value=smax, value=(smin, smax), step=10)
    
    return selected_types, min_price, max_price, (rooms_min, rooms_max), (surface_min, surface_max)

def table_preview(df, n):
    cols = ["title", "listing_type", "price", "rooms", "surface", "address", "url"]
    show_cols = [c for c in cols if c in df.columns]
    if len(df):
        st.dataframe(
            df[show_cols].sort_values("price", ascending=False).head(n),
            use_container_width=True
        )
    else:
        st.info("Aucune ligne après filtres.")

def render_map_properties(df):
    # on garde uniquement les annonces contenant des infos sur leur geoloc
    m = df.dropna(subset=["latitude", "longitude"]).copy()
    if m.empty:
        return None

    # types numériques
    m["latitude"]  = pd.to_numeric(m["latitude"], errors="coerce")
    m["longitude"] = pd.to_numeric(m["longitude"], errors="coerce")
    m = m.dropna(subset=["latitude", "longitude"])

    # prix (couleur) - cap à P95
    m["price_num"] = pd.to_numeric(m.get("price"), errors="coerce").fillna(0.0)
    if m["price_num"].notna().any():
        p95 = np.nanpercentile(m["price_num"], 95)
        m["price_cap"] = np.clip(m["price_num"], 0, p95 if p95 > 0 else 1.0)
    else:
        m["price_cap"] = 0.0

    # surface (taille) - cap à P95
    m["surface_num"] = pd.to_numeric(m.get("surface"), errors="coerce").fillna(10.0)
    if m["surface_num"].notna().any():
        s95 = np.nanpercentile(m["surface_num"], 95)
        m["size_col"] = np.clip(m["surface_num"], 1, s95 if s95 > 1 else 10.0)
    else:
        m["size_col"] = 10.0

    # centre auto
    center = {"lat": float(m["latitude"].mean()), "lon": float(m["longitude"].mean())}

    # hover minimal
    hover_cols = [c for c in ["address", "price", "rooms", "surface", "url"] if c in m.columns]

    # carte
    fig = px.scatter_mapbox(
        m,
        lat="latitude",
        lon="longitude",
        color="price_cap",
        size="size_col",
        size_max=24,
        hover_data=hover_cols,
        mapbox_style="open-street-map",
        zoom=3.5,
        center=center,
        color_continuous_scale="turbo",
    )
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
    return fig

def plot_price_distribution(df):
    if "price" in df:
        fig = px.histogram(df, x="price", nbins=50, title="Distribution des prix")
        return fig
    return None

def plot_price_vs_surface(df):
    if "price" in df and "surface" in df:
        fig = px.scatter(
            df, x="surface", y="price", color="listing_type",
            title="Prix vs Surface (m²)", hover_data=["title"],
            color_discrete_map={"rent": "red", "sale": "blue"}
        )
        fig.update_layout(
            xaxis=dict(range=[0, 400]),
            yaxis=dict(range=[-10, 3_000_000])
        )
        return fig
    return None


def plot_rooms_distribution(df):
    if "rooms" in df:
        fig = px.histogram(
            df, x="rooms", color="listing_type", barmode="group",
            title="Distribution des annonces par nombre de chambres",
            color_discrete_map={"rent": "red", "sale": "blue"}
        )
        return fig
    return None

def plot_city_medians(df, top_n=20):
    d = df.copy()
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    d["city"] = d["address"].fillna("").str.split(",").str[1].str.strip()
    d = d.dropna(subset=["price","city"])
    grp = d.groupby("city")["price"].agg(["median","count","mean","std"]).reset_index()
    grp = grp[grp["count"]>=10].sort_values("median", ascending=False).head(top_n)
    fig = px.bar(
        grp, x="city", y="median",
        error_y=grp["std"].fillna(0),
        title="Prix médian par ville (Top N, min 10 annonces)"
    )
    fig.update_layout(xaxis_tickangle=-45, height=420, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def plot_price_per_sqm_violin(df):
    d = df.copy()
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    d["surface"] = pd.to_numeric(d["surface"], errors="coerce")
    d = d.dropna(subset=["price","surface","listing_type"])
    d = d[(d["surface"]>10) & (d["surface"]<10000)]
    d["price_per_sqm"] = d["price"]/d["surface"].replace(0,np.nan)
    d = d.replace([np.inf,-np.inf], np.nan).dropna(subset=["price_per_sqm"])
    # cap à P99 pour lisibilité
    p99 = np.nanpercentile(d["price_per_sqm"], 99)
    d = d[d["price_per_sqm"]<=p99]
    fig = px.violin(
        d, x="listing_type", y="price_per_sqm", box=True, points="suspectedoutliers",
        title="Distribution du prix / m² par type",
        color_discrete_map={"rent": "red", "sale": "blue"}
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def plot_price_by_rooms(df):
    d = df.copy()
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    d["rooms"] = pd.to_numeric(d["rooms"], errors="coerce")
    d = d.dropna(subset=["price","rooms"])
    d["rooms_bin"] = d["rooms"].clip(lower=0, upper=6)
    fig = px.box(
        d, x="rooms_bin", y="price", points="outliers",
        title="Prix par nombre de chambres (boxplot)",
        color_discrete_map={"rent": "red", "sale": "blue"}
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ML

def plot_real_vs_pred(df):
    df = df.dropna(subset=["price","predicted_price"])
    fig = px.scatter(
        df, x="predicted_price", y="price",
        color="confidence_score", 
        color_continuous_scale=["red", "green"],
        hover_data=["title","address","url"],
        labels={"predicted_price":"Prix prédit", "price":"Prix réel"},
        title="Prix réel vs Prix prédit"
    )
    fig.add_shape(type="line", x0=0, y0=0,
                  x1=df["predicted_price"].max(), y1=df["predicted_price"].max(),
                  line=dict(color="red", dash="dash"))
    return fig

def plot_deals_map(df, threshold=0.8):
    if not {"predicted_price","price","latitude","longitude"}.issubset(df.columns):
        return None
    d = df.copy()
    d["underpricing"] = (d["predicted_price"] - d["price"]) / d["predicted_price"]
    d = d[d["underpricing"] > (1-threshold)]  # ex: deals >20% sous le modèle
    fig = px.scatter_mapbox(
        d, lat="latitude", lon="longitude",
        color="underpricing",
        hover_data=["title","price","predicted_price","address"],
        mapbox_style="open-street-map", zoom=3.5,
        title="Carte des bonnes affaires détectées (prix < prédiction)"
    )
    return fig

def plot_ratio(df):
    df = df.dropna(subset=["price","predicted_price"])
    df["ratio"] = df["price"] / df["predicted_price"]
    fig = px.histogram(df, x="ratio", nbins=50, title="Distribution du ratio Prix réel / prédit")
    return fig

def plot_residuals_by_type(df):
    df = df.dropna(subset=["price","predicted_price","property_type"])
    df["residual"] = df["price"] - df["predicted_price"]
    fig = px.box(df, x="property_type", y="residual", points="all", title="Erreurs de prédiction par type de bien")
    return fig

def plot_confidence_vs_error(df):
    df = df.dropna(subset=["price","predicted_price","confidence_score"])
    df["abs_error"] = (df["price"] - df["predicted_price"]).abs()
    fig = px.scatter(df, x="confidence_score", y="abs_error",
                     color="listing_type",
                     color_discrete_map={"rent": "red","sale": "blue"},
                     hover_data=["title","address","url"],
                     title="Erreur absolue vs Confiance du modèle")
    return fig
