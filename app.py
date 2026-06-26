import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="Toyota Fleet Fraud Dashboard",
    layout="wide"
)

# =========================
# DARK PREMIUM UI
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#081225 0%,#0f172a 100%);
    color: white;
}
html, body, [class*="css"] {
    font-size: 18px !important;
}
h1 {
    font-size: 50px !important;
    color: white !important;
}
h2, h3 {
    color: white !important;
}
[data-testid="stMetricValue"] {
    font-size: 42px !important;
    color: #00ff99 !important;
    font-weight: bold;
}
[data-testid="stMetricLabel"] {
    font-size: 22px !important;
    color: #d1d5db !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🚛 Toyota Fleet Fraud Dashboard")
st.markdown("### Smart Driver Analytics & Fraud Detection")

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

# =========================
# HELPERS
# =========================
def normalize_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("إ", "ا")
        .str.replace("أ", "ا")
        .str.replace("آ", "ا")
        .str.replace("ى", "ي")
        .str.replace("ة", "ه")
    )
    return df

def risk_band(score):
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df = normalize_columns(df)

    # Required columns
    driver_col = "اسم السائق"
    destination_col = "الوجهه"
    fuel_col = "سولار"
    cost_col = "اجمالي المبلغ"
    km_col = "اجمالي الكيلومتر اليومي"
    km_l_col = "عدد الكيلو فى اللتر"

    numeric_cols = [
        fuel_col,
        cost_col,
        km_col,
        km_l_col
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    df = df.fillna(0)

    # =========================
    # DRIVER BASELINES
    # =========================
    driver_avg = (
        df.groupby(driver_col)
        .agg({
            fuel_col: "mean",
            km_l_col: "mean"
        })
        .reset_index()
    )

    driver_avg_dict = dict(
        zip(driver_avg[driver_col], driver_avg[km_l_col])
    )

    def calculate_risk(row):
        risk = 0

        fuel = row[fuel_col]
        km_l = row[km_l_col]
        cost = row[cost_col]
        driver = row[driver_col]

        baseline = driver_avg_dict.get(driver, km_l)

        # Fuel anomaly
        if km_l < baseline * 0.8:
            risk += 40

        # Invoice anomaly
        if cost > df[cost_col].mean() * 1.4:
            risk += 30

        # Fuel spike
        if fuel > df[fuel_col].mean() * 1.35:
            risk += 30

        return min(risk, 100)

    df["Risk Score"] = df.apply(
        calculate_risk,
        axis=1
    )

    total_trips = len(df)
    total_fuel = df[fuel_col].sum()
    avg_risk = round(df["Risk Score"].mean())
    suspicious_count = len(
        df[df["Risk Score"] >= 70]
    )

    estimated_loss = suspicious_count * 250


    # =========================
    # TABS
    # =========================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Executive Dashboard",
        "⚔️ Driver Battle",
        "🛣 Route Comparison",
        "🔍 Investigation Center"
    ])

    # =========================
    # TAB 1 — EXECUTIVE
    # =========================
    with tab1:
        st.subheader("Executive Overview")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Trips", total_trips)
        c2.metric("Total Fuel", f"{round(total_fuel,1)} L")
        c3.metric("Estimated Loss", f"EGP {estimated_loss}")
        c4.metric("Fraud Risk", f"{avg_risk}/100")

        st.markdown("---")

        # Fuel by Driver
        driver_fuel = (
            df.groupby(driver_col)[fuel_col]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            driver_fuel,
            x=driver_col,
            y=fuel_col,
            title="Fuel Consumption by Driver",
            text_auto=True
        )

        fig.update_layout(
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            font_color="white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown("---")

        high_risk_driver = (
            df.groupby(driver_col)["Risk Score"]
            .mean()
            .sort_values(ascending=False)
            .index[0]
        )

        st.error(
            f"""
🚨 AI Executive Alert

Highest risk driver: {high_risk_driver}

Suspicious trips detected: {suspicious_count}
Average fleet risk: {avg_risk}/100
Estimated abnormal loss: EGP {estimated_loss}
"""
        )


    # =========================
    # TAB 2 — DRIVER BATTLE
    # =========================
    with tab2:
        st.subheader("⚔️ Akram vs Ibrahim")

        driver_stats = (
            df.groupby(driver_col)
            .agg({
                fuel_col: "mean",
                km_l_col: "mean",
                cost_col: "mean",
                "Risk Score": "mean"
            })
            .reset_index()
        )

        if len(driver_stats) >= 2:
            d1 = driver_stats.iloc[0]
            d2 = driver_stats.iloc[1]

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Driver", d1[driver_col])
                st.metric("Avg Fuel", round(d1[fuel_col], 2))
                st.metric("KM/L", round(d1[km_l_col], 2))
                st.metric("Risk", round(d1["Risk Score"]))

            with col2:
                st.metric("Driver", d2[driver_col])
                st.metric("Avg Fuel", round(d2[fuel_col], 2))
                st.metric("KM/L", round(d2[km_l_col], 2))
                st.metric("Risk", round(d2["Risk Score"]))

            st.markdown("---")

            efficiency_winner = (
                d1[driver_col]
                if d1[km_l_col] > d2[km_l_col]
                else d2[driver_col]
            )

            risk_loser = (
                d1[driver_col]
                if d1["Risk Score"] > d2["Risk Score"]
                else d2[driver_col]
            )

            st.success(f"🏆 Efficiency Winner: {efficiency_winner}")
            st.error(f"🚨 Highest Fraud Probability: {risk_loser}")

    # =========================
    # TAB 3 — ROUTE COMPARISON
    # =========================
    with tab3:
        st.subheader("Route Comparison")

        route_stats = (
            df.groupby([destination_col, driver_col])[fuel_col]
            .mean()
            .reset_index()
        )

        fig_route = px.bar(
            route_stats,
            x=destination_col,
            y=fuel_col,
            color=driver_col,
            barmode="group",
            title="Fuel Consumption by Route"
        )

        fig_route.update_layout(
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            font_color="white"
        )

        st.plotly_chart(
            fig_route,
            use_container_width=True
        )

        st.dataframe(
            route_stats,
            use_container_width=True
        )


    # =========================
    # TAB 4 — INVESTIGATION CENTER
    # =========================
    with tab4:
        st.subheader("🔍 Investigation Center")

        min_risk = st.slider(
            "Minimum Risk Score",
            min_value=0,
            max_value=100,
            value=70
        )

        suspicious_df = df[
            df["Risk Score"] >= min_risk
        ].copy()

        st.metric(
            "Suspicious Trips",
            len(suspicious_df)
        )

        st.dataframe(
            suspicious_df,
            use_container_width=True
        )

        st.markdown("---")

        # Top risky trips
        top_risky = suspicious_df.sort_values(
            by="Risk Score",
            ascending=False
        ).head(5)

        st.subheader("Top 5 Risky Trips")
        st.dataframe(
            top_risky,
            use_container_width=True
        )

        st.markdown("---")

        # AI Recommendations
        high_risk_driver = (
            df.groupby(driver_col)["Risk Score"]
            .mean()
            .sort_values(ascending=False)
            .index[0]
        )

        avg_gap = (
            df.groupby(driver_col)[km_l_col]
            .mean()
        )

        gap_percent = round(
            (
                (avg_gap.max() - avg_gap.min())
                / max(avg_gap.min(), 0.01)
            ) * 100,
            1
        )

        st.warning(
            f"""
🚨 AI Recommendation Engine

1. Audit fuel records for {high_risk_driver}
2. Review diesel invoices and receipts
3. Inspect possible fuel leakage
4. Check unauthorized route deviations
5. Driver efficiency gap detected: {gap_percent}%
"""
        )

else:
    st.info("Please upload Toyota Excel file")

