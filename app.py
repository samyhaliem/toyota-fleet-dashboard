import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Toyota Fleet Dashboard",
    layout="wide"
)

# ---------- Dark Theme ----------
st.markdown("""
<style>
.stApp {
    background-color: #0f172a;
    color: white;
}
[data-testid="stMetricValue"] {
    color: #00ff99;
}
h1,h2,h3 {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🚛 Toyota Fleet Fraud Dashboard")
st.markdown("### Smart Driver Analytics & Fraud Detection")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str)
    df.columns = df.columns.str.strip()

    # ---------- Auto Detect Columns ----------
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

    st.subheader("Detected Columns")
    st.write({
        "driver": driver_col,
        "fuel": fuel_col,
        "km": km_col,
        "cost": cost_col
    })

    # ---------- Clean Numeric ----------
    if fuel_col:
        df[fuel_col] = pd.to_numeric(df[fuel_col], errors="coerce").fillna(0)

    if km_col:
        df[km_col] = pd.to_numeric(df[km_col], errors="coerce").fillna(0)

    if cost_col:
        df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)

    # ---------- KPI ----------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Trips", len(df))

    total_fuel = df[fuel_col].sum() if fuel_col else 0
    col2.metric("Fuel", round(total_fuel, 1))

    drivers = df[driver_col].nunique() if driver_col else 0
    col3.metric("Drivers", drivers)

    total_km = df[km_col].sum() if km_col else 0
    col4.metric("KM", round(total_km, 1))

    # ---------- Driver Comparison ----------
    if driver_col and fuel_col:
        st.subheader("Driver Fuel Comparison")

        fuel_chart = (
            df.groupby(driver_col)[fuel_col]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            fuel_chart,
            x=driver_col,
            y=fuel_col,
            title="Fuel Consumption by Driver"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------- Suspicious Trips ----------
    if fuel_col:
        threshold = df[fuel_col].mean() * 1.5

        suspicious = df[df[fuel_col] > threshold]

        st.subheader("🚨 Suspicious Trips")

        if len(suspicious) > 0:
            st.dataframe(suspicious)
        else:
            st.success("No suspicious trips detected")

    st.subheader("Raw Data")
    st.dataframe(df)

else:
    st.info("Upload Excel file")
