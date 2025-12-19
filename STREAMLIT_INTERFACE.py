# ==============================
# 1) FONCTIONS DE CHARGEMENT
# ==============================

# On suppose que FILES et BASE_DIR viennent du bloc 0 :
# FILES = {
#     "universe": BASE_DIR / "UNIVERS_ACTIONS_GLOBAL.xlsx",
#     "prices": BASE_DIR / "ALL_PRICES_GLOBAL.xlsx",
#     "portfolio": BASE_DIR / "PORTFOLIO_ULTIMATE_RESULTS.xlsx",
#     "qmf_results": BASE_DIR / "PORTFOLIO_QMF_ANALYSIS.xlsx",
# }

from pathlib import Path
import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# === Définition des fichiers si FILES n'existe pas déjà ===

BASE_DIR = Path(r"C:\Users\Utilisateur\Desktop\CODE")

try:
    FILES
except NameError:
    BASE_DIR = Path(".")  # ou Path("C:/Users/Utilisateur/Desktop/CODE") si tu veux être explicite

    FILES = {
        "universe": BASE_DIR / "UNIVERS_ACTIONS_GLOBAL.xlsx",
        "prices": BASE_DIR / "ALL_PRICES_GLOBAL.xlsx",
        "portfolio": BASE_DIR / "PORTFOLIO_ULTIMATE_RESULTS.xlsx",
        "qmf_results": BASE_DIR / "PORTFOLIO_QMF_ANALYSIS.xlsx",
    }

# ---------- 1.1 Univers (GLOBAL_FULL / GLOBAL_EFFECTIVE) ----------

@st.cache_data(show_spinner=False)
def load_universe():
    """
    Charge le fichier d'univers actions global :
    - GLOBAL_FULL     : univers théorique (tous les titres)
    - GLOBAL_EFFECTIVE: univers effectif (ceux qui ont des prix)

    Returns
    -------
    global_full : DataFrame ou None
    global_eff  : DataFrame ou None
    """
    path = FILES["universe"]
    if not path.exists():
        return None, None

    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return None, None

    def _safe_read(sheet_name):
        if sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            # Si ticker est présent -> en index
            if "ticker" in df.columns:
                df = df.drop_duplicates(subset=["ticker"]).set_index("ticker")
            return df
        return None

    global_full = _safe_read("GLOBAL_FULL")
    global_eff  = _safe_read("GLOBAL_EFFECTIVE")

    return global_full, global_eff


# ---------- 1.2 Prix globaux ----------

@st.cache_data(show_spinner=False)
def load_prices():
    """
    Charge la base de prix globaux (ALL_PRICES_GLOBAL.xlsx).

    Returns
    -------
    prices : DataFrame (dates x tickers) ou None
    """
    path = FILES["prices"]
    if not path.exists():
        return None

    prices = pd.read_excel(path, index_col=0)
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()
    # On ne force pas le numeric partout (certains tickers peuvent être exotiques),
    # mais on enlève les colonnes totalement vides.
    prices = prices.dropna(how="all", axis=1)
    return prices


# ---------- 1.3 Résultats du script de construction de portefeuilles ----------

@st.cache_data(show_spinner=False)
def load_portfolios():
    """
    Charge les résultats du script de construction de portefeuilles
    (PORTFOLIO_ULTIMATE_RESULTS.xlsx).

    Contenu :
    - benchmarks       : DataFrame ou None
    - profiles_perf    : DataFrame (Profiles_Perf)
    - profiles_factor  : DataFrame (Profiles_Factor_Expo)
    - portfolio_names  : liste des noms de portefeuilles
    - details          : dict[name] -> DataFrame détails du portefeuille
    - returns          : DataFrame (dates x portefeuilles) de rendements journaliers
    - risk_contrib     : dict[name] -> DataFrame contributions au risque par titre
    - sector_risk      : dict[name] -> DataFrame risque par secteur
    - region_risk      : dict[name] -> DataFrame risque par région
    """
    path = FILES["portfolio"]
    if not path.exists():
        return None

    xls = pd.ExcelFile(path)

    # Benchmarks globaux
    benchmarks = None
    if "Benchmarks" in xls.sheet_names:
        benchmarks = pd.read_excel(xls, "Benchmarks")

    # Perf & factor expos (obligatoires pour ton projet)
    profiles_perf = pd.read_excel(xls, "Profiles_Perf")
    profiles_factor = pd.read_excel(xls, "Profiles_Factor_Expo")

    if "Profile" not in profiles_perf.columns:
        raise ValueError("La feuille 'Profiles_Perf' doit contenir une colonne 'Profile'.")

    portfolio_names = profiles_perf["Profile"].dropna().unique().tolist()

    details_dict = {}
    returns_dict = {}
    risk_contrib_dict = {}
    sector_risk_dict = {}
    region_risk_dict = {}

    for name in portfolio_names:
        # ----- Détail du portefeuille -----
        sheet_detail = f"{name}_DETAIL"
        if sheet_detail in xls.sheet_names:
            df_det = pd.read_excel(xls, sheet_name=sheet_detail, index_col=0)
            details_dict[name] = df_det

        # ----- Risk contributions par titre -----
        sheet_rc = f"{name}_RISK_CONTRIB"
        if sheet_rc in xls.sheet_names:
            df_rc = pd.read_excel(xls, sheet_name=sheet_rc, index_col=0)
            risk_contrib_dict[name] = df_rc

        # ----- Risk par secteur -----
        sheet_rs = f"{name}_RISK_SECTOR"
        if sheet_rs in xls.sheet_names:
            df_rs = pd.read_excel(xls, sheet_name=sheet_rs, index_col=0)
            sector_risk_dict[name] = df_rs

        # ----- Risk par région -----
        sheet_rr = f"{name}_RISK_REGION"
        if sheet_rr in xls.sheet_names:
            df_rr = pd.read_excel(xls, sheet_name=sheet_rr, index_col=0)
            region_risk_dict[name] = df_rr

        # ----- Returns journaliers -----
        sheet_ret = f"{name}_RETURNS"
        if sheet_ret in xls.sheet_names:
            df_ret = pd.read_excel(xls, sheet_name=sheet_ret, index_col=0)
            df_ret.index = pd.to_datetime(df_ret.index)
            # On prend la première colonne comme série de rendements du portefeuille
            s_ret = pd.to_numeric(df_ret.iloc[:, 0], errors="coerce")
            s_ret.name = name
            returns_dict[name] = s_ret

    if returns_dict:
        returns_all = pd.concat(returns_dict.values(), axis=1).sort_index()
    else:
        returns_all = pd.DataFrame()

    return {
        "benchmarks": benchmarks,
        "profiles_perf": profiles_perf,
        "profiles_factor": profiles_factor,
        "portfolio_names": portfolio_names,
        "details": details_dict,
        "returns": returns_all,
        "risk_contrib": risk_contrib_dict,
        "sector_risk": sector_risk_dict,
        "region_risk": region_risk_dict,
    }


# ---------- 1.4 Résultats QMF (analyse stats, CAPM, PCA…) ----------

@st.cache_data(show_spinner=False)
def load_qmf():
    """
    Charge les résultats du script QMF (PORTFOLIO_QMF_ANALYSIS.xlsx).

    Contenu renvoyé :
    - perf_risk    : DataFrame stats de performance & risque absolu
    - perf_active  : DataFrame performance active vs marché (si présente)
    - capm         : DataFrame résultats CAPM vs marché
    - correlations : DataFrame matrice de corrélation portefeuilles + marché
    - pca_loadings : DataFrame loadings PCA (portefeuilles x PC)
    - pca_eig      : DataFrame valeurs propres & variance expliquée
    - daily_returns: DataFrame rendements journaliers portefeuilles + marché (si présent)
    """
    path = FILES["qmf_results"]
    if not path.exists():
        return None

    xls = pd.ExcelFile(path)

    # Perf & risque absolu (obligatoire dans ton script QMF)
    perf_risk = pd.read_excel(xls, "Perf_Risk_Stats")
    if "Portfolio" in perf_risk.columns:
        perf_risk = perf_risk.set_index("Portfolio")

    # Perf active vs marché (optionnelle, selon la version de ton script QMF)
    perf_active = None
    if "Perf_Active_vs_Mkt" in xls.sheet_names:
        perf_active = pd.read_excel(xls, "Perf_Active_vs_Mkt")
        if "Portfolio" in perf_active.columns:
            perf_active = perf_active.set_index("Portfolio")

    # CAPM vs marché
    capm = pd.read_excel(xls, "CAPM_vs_Market")
    if "Portfolio" in capm.columns:
        capm = capm.set_index("Portfolio")

    # Corrélations
    correlations = pd.read_excel(xls, "Correlations", index_col=0)

    # PCA : loadings & eigenvalues / explained variance
    try:
        pca_loadings = pd.read_excel(xls, "PCA_Loadings", index_col=0)
    except Exception:
        pca_loadings = None

    try:
        pca_eig = pd.read_excel(xls, "PCA_Eigenvalues", index_col=0)
    except Exception:
        pca_eig = None

    # Rendements journaliers portefeuilles + marché (optionnel)
    daily_returns = None
    for candidate_sheet in ["Daily_Returns", "Daily_Returns_Portfolios_Market"]:
        if candidate_sheet in xls.sheet_names:
            daily_returns = pd.read_excel(xls, candidate_sheet, index_col=0)
            daily_returns.index = pd.to_datetime(daily_returns.index)
            break

    return {
        "perf_risk": perf_risk,
        "perf_active": perf_active,
        "capm": capm,
        "correlations": correlations,
        "pca_loadings": pca_loadings,
        "pca_eig": pca_eig,
        "daily_returns": daily_returns,
    }


# ---------- 1.5 Chargement effectif (en mémoire) ----------

global_full, global_eff = load_universe()
prices_global = load_prices()
port_data = load_portfolios()
qmf_data = load_qmf()

# ==============================
# 2) SIDEBAR
# ==============================

# --- Style global (CSS) pour rendre le dashboard plus lisible / pro ---
st.markdown("""
<style>
/* Police un tout petit peu plus petite sur les labels des métriques
   + autoriser le retour à la ligne pour éviter le "..." coupé */
[data-testid="stMetricLabel"] {
    font-size: 0.85rem;
    white-space: normal;
}

/* Valeur des métriques un peu plus grosse et claire */
[data-testid="stMetricValue"] {
    font-size: 1.7rem;
    font-weight: 600;
}

/* Titre principal plus rapproché du haut */
h1 {
    margin-top: 0.5rem;
}

/* Légère réduction de la largeur des containers pour éviter que ça colle aux bords */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Options & Navigation")

# --- Navigation principale ---
page = st.sidebar.radio(
    "🧭 Section principale",
    options=[
        "Vue globale",
        "Univers & Prix",
        "Portefeuilles",
        "Analyse QMF",
    ],
    index=0,
    help="Choisis la vue que tu veux explorer dans le dashboard.",
)

# On garde aussi tes toggles (pour conditionner l'affichage plus finement dans le main)
st.sidebar.markdown("### 🎛 Onglets disponibles")

show_universe_tab = st.sidebar.checkbox(
    "Afficher l'onglet Univers & Prix",
    value=True,
)
show_portfolio_tab = st.sidebar.checkbox(
    "Afficher l'onglet Portefeuilles",
    value=True,
)
show_qmf_tab = st.sidebar.checkbox(
    "Afficher l'onglet Analyse QMF",
    value=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Fichiers attendus")

# Affichage dynamique de l'état des fichiers
file_rows = []
for label, key in [
    ("Univers actions", "universe"),
    ("Prix globaux", "prices"),
    ("Portefeuilles (construction)", "portfolio"),
    ("Analyse QMF", "qmf_results"),
]:
    path = FILES[key]
    exists = path.exists()
    status = "✅" if exists else "❌"
    file_rows.append(f"{status} {label}  —  {path.name}")

st.sidebar.code("\n".join(file_rows), language="text")

# On expose 'page' pour l'utiliser plus bas dans le script
CURRENT_PAGE = page

# ==============================
# 3) CONTENU PRINCIPAL
# ==============================

# Petits helpers pour savoir ce qui est dispo
has_universe  = (global_full is not None) or (global_eff is not None)
has_prices    = prices_global is not None
has_portfolios = (port_data is not None) and (not port_data["returns"].empty)
has_qmf       = qmf_data is not None

# -------- Vue globale (page d’accueil) --------
if CURRENT_PAGE == "Vue globale":
    st.subheader("Vue d’ensemble des analyses")

    st.markdown("##### Indicateurs clés")

    # Colonnes un peu mieux proportionnées
    col1, col2, col3, col4 = st.columns([1.1, 1, 1.3, 1])

    with col1:
        n_univ = 0
        if has_universe:
            if global_eff is not None:
                n_univ = len(global_eff)
            elif global_full is not None:
                n_univ = len(global_full)
        st.metric("Actions (univers effectif)", f"{n_univ:,}")

    with col2:
        n_ports = 0 if not has_portfolios else len(port_data["portfolio_names"])
        st.metric("Portefeuilles", n_ports)

    with col3:
        if has_prices:
            start_date = prices_global.index.min().date()
            end_date   = prices_global.index.max().date()
            st.metric("Période de prix", f"{start_date} → {end_date}")
        else:
            st.metric("Période de prix", "N/A")

    with col4:
        if has_qmf and "perf_risk" in qmf_data and qmf_data["perf_risk"] is not None:
            if "n_obs" in qmf_data["perf_risk"].columns:
                n_days = qmf_data["perf_risk"]["n_obs"].max()
                st.metric("Obs max (QMF)", int(n_days))
            else:
                st.metric("Obs max (QMF)", "N/A")
        else:
            st.metric("Obs max (QMF)", "N/A")

    st.markdown("---")

# -------- Univers & Prix --------
elif CURRENT_PAGE == "Univers & Prix" and show_universe_tab:
    st.subheader("Univers d’actions & séries de prix")

    if not has_universe and not has_prices:
        st.error("Ni univers ni séries de prix trouvés. Vérifie que les fichiers sont bien présents dans le dossier.")
    else:
        tab1, tab2 = st.tabs(["📚 Univers d’actions", "💶 Prix globaux"])

        # =======================
        # TAB 1 : UNIVERS
        # =======================
        with tab1:
            st.markdown("### Univers d’actions")

            if global_full is None and global_eff is None:
                st.warning("Impossible de trouver ni `GLOBAL_FULL` ni `GLOBAL_EFFECTIVE` dans UNIVERS_ACTIONS_GLOBAL.xlsx.")
            else:
                col_u1, col_u2 = st.columns(2)

                # Univers théorique
                with col_u1:
                    st.markdown("#### Univers théorique (`GLOBAL_FULL`)")
                    if global_full is not None and not global_full.empty:
                        st.write(f"Nombre total de lignes : **{len(global_full):,}**")
                        st.dataframe(global_full.head(200), use_container_width=True)
                    else:
                        st.info("Feuille `GLOBAL_FULL` non trouvée ou vide.")

                # Univers effectif
                with col_u2:
                    st.markdown("#### Univers effectif (`GLOBAL_EFFECTIVE`)")
                    if global_eff is not None and not global_eff.empty:
                        st.write(f"Nombre total de lignes : **{len(global_eff):,}**")
                        st.dataframe(global_eff.head(200), use_container_width=True)
                    else:
                        st.info("Feuille `GLOBAL_EFFECTIVE` non trouvée ou vide.")

                st.markdown("---")
                st.markdown("#### Répartition de l’univers effectif")

                if global_eff is not None and not global_eff.empty:
                    col_r, col_s = st.columns(2)

                    # Répartition par région
                    with col_r:
                        if "region" in global_eff.columns:
                            st.caption("Par région")
                            region_counts = global_eff["region"].value_counts().sort_values(ascending=False)
                            st.dataframe(region_counts.to_frame("Nb titres"), use_container_width=True)
                            st.bar_chart(region_counts)
                        else:
                            st.info("Colonne `region` absente de `GLOBAL_EFFECTIVE`.")

                    # Répartition par secteur
                    with col_s:
                        # On privilégie sector_clean si dispo, sinon sector brut
                        sector_col = None
                        if "sector_clean" in global_eff.columns:
                            sector_col = "sector_clean"
                        elif "sector" in global_eff.columns:
                            sector_col = "sector"

                        if sector_col is not None:
                            st.caption(f"Par secteur ({sector_col})")
                            sector_counts = global_eff[sector_col].value_counts().head(15)
                            st.dataframe(sector_counts.to_frame("Nb titres (top 15)"), use_container_width=True)
                            st.bar_chart(sector_counts)
                        else:
                            st.info("Aucune colonne `sector` / `sector_clean` trouvée dans `GLOBAL_EFFECTIVE`.")
                else:
                    st.info("Univers effectif vide : pas de statistiques de répartition possibles.")

        # =======================
        # TAB 2 : PRIX
        # =======================
        with tab2:
            st.markdown("### Séries de prix globales")

            if has_prices and prices_global is not None and not prices_global.empty:
                # Infos de base
                st.write(
                    f"Période disponible : **{prices_global.index.min().date()} → "
                    f"{prices_global.index.max().date()}** "
                    f" | Nombre de titres : **{prices_global.shape[1]}**"
                )

                # Sélection des tickers à visualiser
                all_tickers = prices_global.columns.tolist()
                default_tickers = all_tickers[: min(10, len(all_tickers))]

                selected_tickers = st.multiselect(
                    "Sélectionne les titres à afficher",
                    options=all_tickers,
                    default=default_tickers,
                )

                normalize = st.checkbox("Normaliser les prix (base 100 au début de la période)", value=True)

                if selected_tickers:
                    prices_sub = prices_global[selected_tickers].copy()

                    if normalize:
                        # Base 100 sur la première date où on a toutes les séries choisies
                        first_valid_idx = prices_sub.dropna().index.min()
                        if pd.isna(first_valid_idx):
                            st.warning("Impossible de normaliser : pas de date commune avec toutes les séries non NA.")
                        else:
                            base = prices_sub.loc[first_valid_idx]
                            prices_sub = prices_sub.div(base) * 100
                            st.caption(f"Normalisation : base 100 au {first_valid_idx.date()}.")

                    st.line_chart(prices_sub, use_container_width=True)
                else:
                    st.info("Sélectionne au moins un ticker pour afficher un graphique.")

                with st.expander("Aperçu brut des données de prix (head)", expanded=False):
                    st.dataframe(prices_global.head(), use_container_width=True)

            else:
                st.warning("Aucun fichier de prix valide trouvé (`ALL_PRICES_GLOBAL.xlsx`).")

# -------- Portefeuilles --------
elif CURRENT_PAGE == "Portefeuilles" and show_portfolio_tab:
    st.subheader("Analyse détaillée des portefeuilles")

    if not has_portfolios:
        st.error("Aucun portefeuille trouvé dans PORTFOLIO_ULTIMATE_RESULTS.xlsx")
    else:
        names = port_data["portfolio_names"]
        selected = st.selectbox("Choisir un portefeuille", names)

        # Méta & rendements de ce portefeuille
        det = port_data["details"].get(selected)
        rets = (
            port_data["returns"][selected]
            if hasattr(port_data["returns"], "columns") and selected in port_data["returns"].columns
            else None
        )

        # Stats QMF si disponibles
        qmf_perf_row = None
        if has_qmf and "perf_risk" in qmf_data and qmf_data["perf_risk"] is not None:
            if selected in qmf_data["perf_risk"].index:
                qmf_perf_row = qmf_data["perf_risk"].loc[selected]

        col_top1, col_top2 = st.columns([2, 1])

        # =========================
        # 2.1 Composition du portefeuille
        # =========================
        with col_top1:
            st.markdown("### 🧱 Composition du portefeuille")

            if det is not None and not det.empty:
                st.dataframe(det, use_container_width=True)

                # Poids par secteur / région si colonnes dispo
                st.markdown("#### Répartition des poids")

                c1, c2 = st.columns(2)

                if "weight" in det.columns:
                    # Par secteur
                    with c1:
                        if "sector" in det.columns:
                            sector_w = det.groupby("sector")["weight"].sum().sort_values(ascending=False)
                            st.caption("Poids par secteur")
                            st.dataframe(sector_w.to_frame("Poids"), use_container_width=True)
                            st.bar_chart(sector_w)
                        else:
                            st.info("Colonne `sector` absente de la feuille *_DETAIL.")

                    # Par région
                    with c2:
                        if "region" in det.columns:
                            region_w = det.groupby("region")["weight"].sum().sort_values(ascending=False)
                            st.caption("Poids par région")
                            st.dataframe(region_w.to_frame("Poids"), use_container_width=True)
                            st.bar_chart(region_w)
                        else:
                            st.info("Colonne `region` absente de la feuille *_DETAIL.")
                else:
                    st.info("Colonne `weight` non trouvée : impossible d’agréger les poids.")
            else:
                st.info("Pas de feuille *_DETAIL pour ce portefeuille.")

        # =========================
        # 2.2 Stats rapides (QMF)
        # =========================
        with col_top2:
            st.markdown("### ⚡ Stats rapides (QMF)")

            if qmf_perf_row is not None:
                # On extrait quelques indicateurs clés
                kpi_cols = ["ann_ret", "ann_vol", "Sharpe", "Sortino", "MaxDD"]
                for k in list(kpi_cols):
                    if k not in qmf_perf_row.index:
                        kpi_cols.remove(k)

                if kpi_cols:
                    # Affichage sous forme de métriques
                    st.caption("Indicateurs clés (annualisés)")

                    # On essaye de garder un layout propre
                    col_kpi1, col_kpi2 = st.columns(2)
                    with col_kpi1:
                        if "ann_ret" in qmf_perf_row.index:
                            st.metric(
                                "Rendement annuel",
                                f"{qmf_perf_row['ann_ret']:.2%}"
                            )
                        if "Sharpe" in qmf_perf_row.index:
                            st.metric(
                                "Sharpe",
                                f"{qmf_perf_row['Sharpe']:.2f}"
                            )
                        if "Sortino" in qmf_perf_row.index:
                            st.metric(
                                "Sortino",
                                f"{qmf_perf_row['Sortino']:.2f}"
                            )

                    with col_kpi2:
                        if "ann_vol" in qmf_perf_row.index:
                            st.metric(
                                "Vol annualisée",
                                f"{qmf_perf_row['ann_vol']:.2%}"
                            )
                        if "MaxDD" in qmf_perf_row.index:
                            st.metric(
                                "Max Drawdown",
                                f"{qmf_perf_row['MaxDD']:.2%}"
                            )

                with st.expander("Voir toutes les stats QMF pour ce portefeuille"):
                    st.dataframe(qmf_perf_row.to_frame().T, use_container_width=True)

            else:
                st.info("Stats QMF non disponibles pour ce portefeuille (pas dans `Perf_Risk_Stats`).")

        st.markdown("---")

        # =========================
        # 2.3 Performance historique
        # =========================
        st.markdown("### 📈 Performance historique")

        if rets is not None and not rets.empty:
            # Série de rendements
            st.markdown("#### Rendements journaliers")
            st.line_chart(rets.to_frame(name=selected), use_container_width=True)

            # Performance cumulée vs marché (si QMF daily_returns contient MKT_EW)
            if has_qmf and qmf_data.get("daily_returns") is not None:
                daily = qmf_data["daily_returns"].copy()
                if selected in daily.columns and "MKT_EW" in daily.columns:
                    port_series, mkt_series = daily[selected].align(daily["MKT_EW"], join="inner")
                    cum_port = (1 + port_series).cumprod()
                    cum_mkt = (1 + mkt_series).cumprod()

                    st.markdown("#### Performance cumulée vs marché global (MKT_EW)")
                    df_cum = pd.concat(
                        [cum_port.rename(selected), cum_mkt.rename("MKT_EW")],
                        axis=1
                    )
                    st.line_chart(df_cum, use_container_width=True)
                else:
                    st.info("La feuille QMF ne contient pas `Daily_Returns` avec ce portefeuille et `MKT_EW`.")
            else:
                st.info("Fichier QMF sans `Daily_Returns` : comparaison directe avec le marché indisponible.")
        else:
            st.info("Rendements journaliers non trouvés pour ce portefeuille.")

# -------- Analyse QMF --------
elif CURRENT_PAGE == "Analyse QMF" and show_qmf_tab:
    st.subheader("Analyse QMF – Performance, CAPM, Corrélations, PCA")

    if not has_qmf:
        st.error("Fichier QMF introuvable. Vérifie PORTFOLIO_QMF_ANALYSIS.xlsx")
    else:
        qmf_tabs = st.tabs(["Perf & risque", "CAPM & alpha", "Corrélations", "PCA"])

        # =========================
        # 1) PERF & RISQUE
        # =========================
        with qmf_tabs[0]:
            st.markdown("### 📊 Statistiques de performance & risque")

            perf_risk = qmf_data.get("perf_risk")
            perf_active = qmf_data.get("perf_active")

            if perf_risk is None or perf_risk.empty:
                st.warning("Table `Perf_Risk_Stats` vide ou introuvable dans le fichier QMF.")
            else:
                # Choix des colonnes clés pour affichage formaté
                default_cols = ["ann_ret", "ann_vol", "Sharpe", "Sortino", "MaxDD"]
                cols_present = [c for c in default_cols if c in perf_risk.columns]

                with st.expander("Table complète des stats de performance & risque", expanded=True):
                    # Formatage simple : % sur les colonnes de rendement / vol / drawdown
                    fmt_dict = {}
                    for col in perf_risk.columns:
                        if any(k in col.lower() for k in ["ret", "vol", "dd", "var", "es"]):
                            fmt_dict[col] = "{:.2%}".format
                        else:
                            fmt_dict[col] = "{:.4f}".format

                    st.dataframe(
                        perf_risk.style.format(fmt_dict),
                        use_container_width=True
                    )

                # Petits graphiques de synthèse : rendement / vol / Sharpe
                if cols_present:
                    st.markdown("#### Vue synthétique : rendement / risque / Sharpe")

                    col_a, col_b = st.columns(2)

                    # Scatter ann_ret vs ann_vol
                    with col_a:
                        if {"ann_ret", "ann_vol"}.issubset(perf_risk.columns):
                            fig, ax = plt.subplots(figsize=(5, 4))
                            x = perf_risk["ann_vol"]
                            y = perf_risk["ann_ret"]
                            ax.scatter(x, y)

                            for label in perf_risk.index:
                                ax.annotate(label, (x.loc[label], y.loc[label]), fontsize=8, alpha=0.7)

                            ax.set_xlabel("Vol annualisée")
                            ax.set_ylabel("Rendement annualisé")
                            ax.set_title("Risque / Rendement (portefeuilles)")
                            ax.grid(True, alpha=0.3)
                            st.pyplot(fig, clear_figure=True)
                        else:
                            st.info("Colonnes `ann_ret` / `ann_vol` manquantes pour tracer le scatter.")

                    # Barplot du Sharpe
                    with col_b:
                        if "Sharpe" in perf_risk.columns:
                            fig, ax = plt.subplots(figsize=(5, 4))
                            perf_risk["Sharpe"].sort_values(ascending=False).plot(kind="bar", ax=ax)
                            ax.set_title("Ratio de Sharpe par portefeuille")
                            ax.set_ylabel("Sharpe")
                            ax.grid(True, axis="y", alpha=0.3)
                            st.pyplot(fig, clear_figure=True)
                        else:
                            st.info("Colonne `Sharpe` manquante dans Perf_Risk_Stats.")

                # Perf active vs marché si dispo
                if perf_active is not None and not perf_active.empty:
                    st.markdown("#### 📌 Performance active vs marché (si calculée dans QMF)")

                    st.dataframe(
                        perf_active.style.format(
                            {c: "{:.2%}".format for c in perf_active.columns if "ret" in c.lower() or "vol" in c.lower()}
                        ),
                        use_container_width=True
                    )
                else:
                    st.caption("Perf active vs marché (`Perf_Active_vs_Mkt`) non disponible.")

        # =========================
        # 2) CAPM & ALPHA
        # =========================
        with qmf_tabs[1]:
            st.markdown("### 📐 CAPM vs marché global")

            capm = qmf_data.get("capm")

            if capm is None or capm.empty:
                st.warning("Table `CAPM_vs_Market` introuvable ou vide.")
            else:
                # Table complète
                with st.expander("Table CAPM (alpha, beta, R², t-stats…)", expanded=True):
                    fmt_capm = {}
                    for col in capm.columns:
                        if "alpha" in col.lower() and "pvalue" not in col.lower():
                            fmt_capm[col] = "{:.2%}".format
                        elif "beta" in col.lower():
                            fmt_capm[col] = "{:.3f}".format
                        elif "pvalue" in col.lower():
                            fmt_capm[col] = "{:.3f}".format
                        elif "r2" in col.lower():
                            fmt_capm[col] = "{:.3f}".format
                    st.dataframe(capm.style.format(fmt_capm), use_container_width=True)

                # Scatter alpha_annual vs beta
                if {"alpha_annual", "beta"}.issubset(capm.columns):
                    st.markdown("#### Scatter alpha annuel vs beta (CAPM)")

                    fig, ax = plt.subplots(figsize=(6, 5))
                    x = capm["beta"]
                    y = capm["alpha_annual"]

                    # Point coloré si alpha significatif à 5 %
                    colors = []
                    for idx in capm.index:
                        p = capm.loc[idx, "alpha_pvalue"] if "alpha_pvalue" in capm.columns else np.nan
                        if not np.isnan(p) and p < 0.05:
                            colors.append("tab:red")
                        else:
                            colors.append("tab:blue")

                    ax.scatter(x, y, c=colors)

                    for label in capm.index:
                        ax.annotate(label, (x.loc[label], y.loc[label]), fontsize=8, alpha=0.7)

                    ax.axhline(0, color="grey", linestyle="--", linewidth=1)
                    ax.set_xlabel("Beta (CAPM)")
                    ax.set_ylabel("Alpha annualisé")
                    ax.set_title("Alpha vs Beta – Significativité de l’alpha (p < 5% en rouge)")
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig, clear_figure=True)
                else:
                    st.info("Colonnes `alpha_annual` et `beta` nécessaires pour le scatter CAPM.")

        # =========================
        # 3) CORRÉLATIONS
        # =========================
        with qmf_tabs[2]:
            st.markdown("### 🔗 Corrélations portefeuilles & marché")

            corr = qmf_data.get("correlations")
            if corr is None or corr.empty:
                st.warning("Matrice de corrélation introuvable dans QMF.")
            else:
                st.markdown("#### Matrice numérique")
                st.dataframe(
                    corr.style.format("{:.2f}"),
                    use_container_width=True
                )

                st.markdown("#### Heatmap de corrélation")

                fig, ax = plt.subplots(figsize=(7, 6))
                sns.heatmap(
                    corr,
                    annot=True,
                    fmt=".2f",
                    cmap="coolwarm",
                    center=0,
                    cbar=True,
                    square=True,
                    ax=ax
                )
                ax.set_title("Matrice de corrélation (portefeuilles + marché)")
                st.pyplot(fig, clear_figure=True)

        # =========================
        # 4) PCA
        # =========================
        with qmf_tabs[3]:
            st.markdown("### 🧬 Analyse en Composantes Principales (PCA)")

            pca_eig = qmf_data.get("pca_eig")
            pca_load = qmf_data.get("pca_loadings")

            col_pca1, col_pca2 = st.columns(2)

            # ---- Eigenvalues / variance expliquée ----
            with col_pca1:
                st.markdown("#### Valeurs propres & variance expliquée")

                if pca_eig is not None and not pca_eig.empty:
                    st.dataframe(
                        pca_eig.style.format(
                            {
                                "eigenvalue": "{:.4f}".format,
                                "explained_var": "{:.2%}".format,
                                "cum_explained_var": "{:.2%}".format,
                            }
                        ),
                        use_container_width=True
                    )

                    # Scree plot
                    fig, ax = plt.subplots(figsize=(5, 4))
                    x = np.arange(1, len(pca_eig) + 1)
                    ax.bar(x, pca_eig["explained_var"], label="Explained var")
                    ax.plot(x, pca_eig["cum_explained_var"], marker="o", label="Cumul")
                    ax.set_xlabel("Composante principale")
                    ax.set_ylabel("Variance expliquée")
                    ax.set_title("PCA – Scree plot")
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    st.pyplot(fig, clear_figure=True)
                else:
                    st.info("Table `PCA_Eigenvalues` non trouvée.")

            # ---- Loadings PCA ----
            with col_pca2:
                st.markdown("#### Loadings (portefeuilles dans l’espace des PCs)")

                if pca_load is not None and not pca_load.empty:
                    st.dataframe(pca_load, use_container_width=True)

                    # Scatter PC1 vs PC2
                    if {"PC1", "PC2"}.issubset(pca_load.columns):
                        st.markdown("Scatter PC1 vs PC2 (positionnement des portefeuilles)")

                        fig, ax = plt.subplots(figsize=(5, 4))
                        x = pca_load["PC1"]
                        y = pca_load["PC2"]
                        ax.scatter(x, y)

                        for label in pca_load.index:
                            ax.annotate(label, (x.loc[label], y.loc[label]), fontsize=8, alpha=0.7)

                        ax.axhline(0, color="grey", linewidth=1)
                        ax.axvline(0, color="grey", linewidth=1)
                        ax.set_xlabel("PC1")
                        ax.set_ylabel("PC2")
                        ax.set_title("PCA – PC1 vs PC2")
                        ax.grid(True, alpha=0.3)
                        st.pyplot(fig, clear_figure=True)
                    else:
                        st.info("Colonnes `PC1` et `PC2` absentes des loadings PCA.")
                else:
                    st.info("Table `PCA_Loadings` non trouvée.")


# -------- Sécurité : si aucune page affichée --------
else:
    st.warning("Aucune section sélectionnée ou fichiers manquants.")
