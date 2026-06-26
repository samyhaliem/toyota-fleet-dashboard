import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="Toyota Fleet Fraud Dashboard",
    layout="wide"
)

# =========================
# PREMIUM DARK THEME
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #081225 0%, #0f172a 100%);
    color: white;
}

html, body, [class*="css"] {
    font-size: 18px !important;
}

h1 {
    font-size: 52px !important;
    font-weight: 800 !important;
    color: white !important;
}

h2 {
    font-size: 38px !important;
    color: white !important;
}

h3 {
    font-size: 28px !important;
    color: white !important;
}

[data-testid="stMetricValue"] {
    font-size: 40px !important;
    color: #00ff99 !important;
    font-weight: bold !important;
}

[data-testid="stMetricLabel"] {
    font-size: 22px !important;
    color: #d1d5db !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.title("🚛 Toyota Fleet Fraud Dashboard")
st.markdown("### Smart Driver Analytics & Fuel Fraud Detection")

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

# =========================
# HELPER FUNCTIONS
# =========================
def risk_label(score):
    if score >= 75:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"


def calculate_risk(row, driver_avg):
    risk = 0

    km_liter = row["عدد الكيلو في اللتر"]
    cost_km = row["تكلفة الكيلو"]
    driver = row["اسم السائق"]

    if pd.notna(km_liter):
        if km_liter < 3:
            risk += 40
        elif km_liter < 4:
            risk += 20

    if pd.notna(cost_km):
        if cost_km > 2:
            risk += 30
        elif cost_km > 1.5:
            risk += 15

    if driver in driver_avg:
        if km_liter < driver_avg[driver] * 0.8:
            risk += 30

    return min(risk, 100)

# =========================
# MAIN
# =========================
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # تنظيف
    numeric_cols = [
        "سولار",
        "تكلفة الكيلو",
        "عدد الكيلو في اللتر",
        "إجمالي الكيلومتر اليومي"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    df = df.fillna(0)

    # Driver averages
    driver_avg = (
        df.groupby("اسم السائق")["عدد الكيلو في اللتر"]
        .mean()
        .to_dict()
    )

    # Risk score
    df["Risk Score"] = df.apply(
        lambda row: calculate_risk(row, driver_avg),
        axis=1
    )

    # KPIs
    total_trips = len(df)
    total_fuel = df["سولار"].sum()
    avg_risk = round(df["Risk Score"].mean())
    suspicious_count = len(df[df["Risk Score"] >= 70])

    estimated_loss = suspicious_count * 250


    # =========================
    # TABS
    # =========================
    tab1, tab2, tab3 = st.tabs([
        "📊 Executive Dashboard",
        "🔍 Audit Investigation",
        "⚔️ Driver Battle"
    ])

    # =========================
    # TAB 1: EXECUTIVE
    # =========================
    with tab1:

        st.subheader("Executive Overview")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Trips", total_trips)
        c2.metric("Total Fuel", f"{round(total_fuel,1)} L")
        c3.metric("Estimated Loss", f"EGP {estimated_loss}")
        c4.metric("Fraud Risk", f"{avg_risk}/100")

        st.markdown("---")

        # Driver fuel consumption chart
        driver_summary = (
            df.groupby("اسم السائق")["سولار"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            driver_summary,
            x="اسم السائق",
            y="سولار",
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

        st.warning(
            f"""
🚨 Executive Alert

Suspicious trips detected: {suspicious_count}

Average fleet risk: {avg_risk}/100
"""
        )

    # =========================
    # TAB 2: AUDIT
    # =========================
    with tab2:

        st.subheader("Audit Investigation")

        drivers = ["All"] + list(
            df["اسم السائق"].unique()
        )

        selected_driver = st.selectbox(
            "Filter by Driver",
            drivers
        )

        filtered_df = df.copy()

        if selected_driver != "All":
            filtered_df = filtered_df[
                filtered_df["اسم السائق"]
                == selected_driver
            ]

        risk_filter = st.slider(
            "Minimum Risk Score",
            0,
            100,
            50
        )

        suspicious_df = filtered_df[
            filtered_df["Risk Score"] >= risk_filter
        ]

        st.subheader("Suspicious Trips")

        st.dataframe(
            suspicious_df,
            use_container_width=True
        )

        st.markdown("---")

        st.subheader("All Trips")

        st.dataframe(
            filtered_df,
            use_container_width=True
        )



    # =========================
    # TAB 3: DRIVER BATTLE
    # =========================
    with tab3:

        st.subheader("⚔️ Driver Battle")

        driver_stats = (
            df.groupby("اسم السائق")
            .agg({
                "سولار": "mean",
                "عدد الكيلو في اللتر": "mean",
                "تكلفة الكيلو": "mean",
                "Risk Score": "mean"
            })
            .reset_index()
        )

        if len(driver_stats) >= 2:

            d1 = driver_stats.iloc[0]
            d2 = driver_stats.iloc[1]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(
                    f"""
### 🚗 {d1['اسم السائق']}

Fuel Avg: {round(d1['سولار'],2)} L

KM/L: {round(d1['عدد الكيلو في اللتر'],2)}

Cost/KM: {round(d1['تكلفة الكيلو'],2)}

Risk Score: {round(d1['Risk Score'])}/100
"""
                )

            with col2:
                st.markdown(
                    f"""
### 🚗 {d2['اسم السائق']}

Fuel Avg: {round(d2['سولار'],2)} L

KM/L: {round(d2['عدد الكيلو في اللتر'],2)}

Cost/KM: {round(d2['تكلفة الكيلو'],2)}

Risk Score: {round(d2['Risk Score'])}/100
"""
                )

            st.markdown("---")

            # Winner Logic
            efficiency_winner = (
                d1["اسم السائق"]
                if d1["عدد الكيلو في اللتر"]
                > d2["عدد الكيلو في اللتر"]
                else d2["اسم السائق"]
            )

            low_risk_winner = (
                d1["اسم السائق"]
                if d1["Risk Score"]
                < d2["Risk Score"]
                else d2["اسم السائق"]
            )

            high_risk_driver = (
                d1["اسم السائق"]
                if d1["Risk Score"]
                > d2["Risk Score"]
                else d2["اسم السائق"]
            )

            st.success(
                f"🏆 Efficiency Winner: {efficiency_winner}"
            )

            st.info(
                f"🛡 Lowest Risk Driver: {low_risk_winner}"
            )

            st.error(
                f"🚨 Highest Fraud Probability: {high_risk_driver}"
            )

            st.markdown("---")

            st.subheader("AI Recommendation")

            st.warning(
                f"""
1. Audit fuel records for {high_risk_driver}
2. Review fuel invoices
3. Check idle engine time
4. Inspect fuel leakage possibility
"""
            )

else:
    st.info("Please upload Toyota Excel file")
