import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Fleet Control Dashboard",
    page_icon="🚚",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at top left, rgba(37,99,235,0.12), transparent 28%),
          radial-gradient(circle at top right, rgba(16,185,129,0.10), transparent 22%),
          linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
      }
      .hero {
        padding: 1.1rem 1.2rem;
        border-radius: 22px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 48%, #0f766e 100%);
        color: white;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.22);
        margin-bottom: 1rem;
      }
      .hero h1 {
        margin: 0;
        font-size: 2rem;
        line-height: 1.2;
      }
      .hero p {
        margin: 0.35rem 0 0;
        opacity: 0.92;
        font-size: 0.98rem;
      }
      div[data-testid="stMetric"] {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      }
      section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(148, 163, 184, 0.18);
      }
      .insight-box {
        border-radius: 18px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        padding: 0.95rem 1rem;
        margin: 0.4rem 0 0.75rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_text(value: str) -> str:
    return (
        str(value)
        .strip()
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
    )


def canonicalize(value: str) -> str:
    return (
        normalize_text(value)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace(".", "")
        .replace("/", "")
    )


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def safe_date(series: pd.Series) -> pd.Series:
    values = series.copy()

    if pd.api.types.is_datetime64_any_dtype(values):
        return pd.to_datetime(values, errors="coerce")

    if pd.api.types.is_numeric_dtype(values):
        try:
            return pd.to_datetime(values, errors="coerce", unit="D", origin="1899-12-30")
        except Exception:
            return pd.to_datetime(values, errors="coerce")

    cleaned = (
        values.astype(str)
        .str.replace("\u200f", "", regex=False)
        .str.replace("\u200e", "", regex=False)
        .str.strip()
    )

    parsed = pd.to_datetime(cleaned, errors="coerce", dayfirst=True)
    if parsed.notna().any():
        return parsed

    try:
        return pd.to_datetime(cleaned, errors="coerce")
    except Exception:
        return pd.to_datetime(
            pd.Series([pd.NaT] * len(values), index=values.index),
            errors="coerce",
        )
