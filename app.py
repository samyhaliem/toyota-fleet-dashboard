import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Toyota Fleet Dashboard",
    layout="wide"
)

st.title("🚛 Toyota Fleet Fraud Dashboard")
st.markdown("### Smart Driver Analytics & Fraud Detection")

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("Raw Data")
    st.dataframe(df)

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Trips", len(df))

    if "بنزين / سولار" in df.columns:
        total_fuel = df["بنزين / سولار"].sum()
        col2.metric("Total Fuel", round(total_fuel, 2))

    if "اسم السائق" in df.columns:
        total_drivers = df["اسم السائق"].nunique()
        col3.metric("Drivers", total_drivers)

        fuel_chart = (
            df.groupby("اسم السائق")["بنزين / سولار"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            fuel_chart,
            x="اسم السائق",
            y="بنزين / سولار",
            title="Fuel Consumption by Driver"
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload Toyota Excel file")
