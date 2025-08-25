import streamlit as st
from utils import (
    load_properties,
    load_properties_with_predictions,
    apply_filters,
    kpi,
    sidebar_filters,
    plot_city_medians,
    plot_price_per_sqm_violin,
    plot_price_by_rooms,
    render_map_properties,
    table_preview,
    plot_price_distribution,
    plot_price_vs_surface,
    plot_rooms_distribution,
    plot_real_vs_pred,
    plot_deals_map,
    plot_residuals_by_type,
    plot_confidence_vs_error,
)

st.set_page_config(page_title="Immo — Starter", layout="wide")

df = load_properties()
df2 = load_properties_with_predictions()

selected_types, min_price, max_price, rooms_range, surface_range = sidebar_filters(df)

st.title("🏠 Tableau de bord — ébauche modulaire")
st.caption("Mini app Streamlit, utils séparés.")
f = apply_filters(
    df,
    selected_types=selected_types,
    min_price=min_price,
    max_price=max_price,
    rooms_range=rooms_range,
    surface_range=surface_range
)

# KPI
n, avg, med = kpi(f)
c1, c2, c3 = st.columns(3)
with c1: st.metric("Annonces", f"{n:,}")
with c2: st.metric("Prix moyen", f"{avg:,.0f}")
with c3: st.metric("Prix médian", f"{med:,.0f}")

st.divider()
tab, tab_pred = st.tabs(["Donnée brut", "Prédiction"])

with tab:
    st.caption("Aperçu des données brut du résultat du scrapping effectué.")
    st.subheader("Aperçu")
    table_preview(f, n=30)

    st.divider()
    st.subheader("Carte des annonces")
    fig_map = render_map_properties(f)
    if fig_map is not None:
        st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": True})
    else:
        st.info("Erreur carte.")

    st.divider()
    st.subheader("Graphes principaux")

    fig1 = plot_price_distribution(f)
    if fig1: st.plotly_chart(fig1, use_container_width=True)

    fig2 = plot_price_vs_surface(f)
    if fig2: st.plotly_chart(fig2, use_container_width=True)

    fig4 = plot_rooms_distribution(f)
    if fig4: st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("Analyses avancées")
    st.plotly_chart(plot_city_medians(f, 20), use_container_width=True)
    st.plotly_chart(plot_price_per_sqm_violin(f), use_container_width=True)
    st.plotly_chart(plot_price_by_rooms(f), use_container_width=True)

# ML
with tab_pred:
    st.caption("Aperçu des performances du modèle et des bonnes affaires potentielles.")
    fig_rvp = plot_real_vs_pred(df2)
    if fig_rvp:
        st.plotly_chart(fig_rvp, use_container_width=True)

    fig_res_type = plot_residuals_by_type(df2)
    if fig_res_type:
        st.plotly_chart(fig_res_type, use_container_width=True)

    fig_conf_err = plot_confidence_vs_error(df2)
    if fig_conf_err:
        st.plotly_chart(fig_conf_err, use_container_width=True)

    fig_deals = plot_deals_map(df2, threshold=0.8)
    if fig_deals:
        st.plotly_chart(fig_deals, use_container_width=True, config={"scrollZoom": True})
