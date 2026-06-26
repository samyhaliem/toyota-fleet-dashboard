import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Toyota Fleet Dashboard",
    layout="wide"
)

# =========================
# DARK THEME
# =========================
st.markdown("""
<style>
.stApp {
    background-color: #0f172a;
    color: white;
}
h1,h2,h3,h4 {
    color: white !important;
}
[data-testid="stMetricValue"] {
    color: #00ff99;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def safe_sum(df, col):
    if col and col in df.columns:
        return pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0).sum()
    return 0


def safe_unique(df, col):
    if col and col in df.columns:
        return df[col].nunique()
    return 0


# =========================
# UI HEADER
# =========================
st.title("🚛 Toyota Fleet Fraud Dashboard")
st.markdown("### Smart Driver Analytics & Fraud Detection")

tab1, tab2 = st.tabs([
    "📊 Executive Dashboard",
    "🔍 Audit Investigation"
])

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded_file:

    # =========================
    # LOAD DATA
    # =========================
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str)
    df.columns = df.columns.str.strip()

    # =========================
    # AUTO DETECT COLUMNS
    # =========================
    driver_col = None
    fuel_col = None
    km_col = None
    cost_col = None

    for col in df.columns:

        if "السائق" in col:
            driver_col = col

        if "سولار" in col or "بنزين" in col:
            fuel_col = col

        if "الكيلومتر" in col:
            km_col = col

        if "تكلفة الكيلو" in col:
            cost_col = col

    # =========================
    # CLEAN NUMERIC
    # =========================
    if fuel_col:
        df[fuel_col] = pd.to_numeric(
            df[fuel_col],
            errors="coerce"
        ).fillna(0)

    if km_col:
        df[km_col] = pd.to_numeric(
            df[km_col],
            errors="coerce"
        ).fillna(0)

    if cost_col:
        df[cost_col] = pd.to_numeric(
            df[cost_col],
            errors="coerce"
        ).fillna(0)

    # =========================
    # KPI CALCULATIONS
    # =========================
    total_trips = len(df)
    total_fuel = safe_sum(df, fuel_col)
    total_km = safe_sum(df, km_col)
    drivers = safe_unique(df, driver_col)

    expected_fuel = total_km / 12 if total_km > 0 else 0
    estimated_loss = max(0, total_fuel - expected_fuel) * 10

    fraud_score = min(
        100,
        round((estimated_loss / 1000) * 20)
    )

    # =========================
    # EXECUTIVE TAB
    # =========================
    with tab1:

        st.subheader("Executive Overview")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Trips", total_trips)
        c2.metric("Fuel", f"{round(total_fuel,1)} L")
        c3.metric("Loss", f"EGP {round(estimated_loss,0)}")
        c4.metric("Risk", f"{fraud_score}/100")

        st.markdown("---")

        if driver_col and fuel_col:

            ranking = (
                df.groupby(driver_col)[fuel_col]
                .sum()
                .reset_index()
                .sort_values(
                    by=fuel_col,
                    ascending=False
                )
            )

            fig = px.bar(
                ranking,
                x=driver_col,
                y=fuel_col,
                title="Driver Risk Ranking"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            top_driver = ranking.iloc[0][driver_col]

            st.error(
                f"""
🚨 EXECUTIVE ALERT

High fuel anomaly detected.

Highest Risk Driver: {top_driver}

Immediate audit recommended.
"""
            )

    # =========================
    # AUDIT TAB
    # =========================
    with tab2:

        st.subheader("Audit Investigation")

        if fuel_col:
            threshold = df[fuel_col].mean() * 1.5
            suspicious = df[df[fuel_col] > threshold]

            st.subheader("🚨 Suspicious Trips")

            if len(suspicious) > 0:
                st.dataframe(
                    suspicious,
                    use_container_width=True
                )
            else:
                st.success(
                    "No suspicious trips detected"
                )

        st.subheader("All Trip Records")
        st.dataframe(
            df,
            use_container_width=True
        )

else:
    st.info("Upload Toyota Excel file")
