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
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def load_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    raise ValueError("Upload CSV or Excel file.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    copy = df.copy()
    copy.columns = [normalize_text(col) for col in copy.columns]
    return copy


def detect_column(columns: list[str], keyword_groups: list[list[str]]) -> str | None:
    normalized = {col: canonicalize(col) for col in columns}
    for group in keyword_groups:
        keywords = [canonicalize(k) for k in group]
        for col in columns:
            value = normalized[col]
            if any(keyword and keyword in value for keyword in keywords):
                return col
    return None


def detect_schema(df: pd.DataFrame) -> dict[str, str | None]:
    cols = list(df.columns)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return {
        "date": detect_column(cols, [["التاريخ", "date", "day"], ["تاريخ"]]),
        "driver": detect_column(cols, [["اسم السائق", "driver", "name"], ["السائق"]]),
        "destination": detect_column(cols, [["الوجهه", "destination", "route"], ["وجهة", "trip"]]),
        "daily_km": detect_column(numeric_cols, [["اجمالى الكيلومتر اليومى", "dailykm", "distance", "tripkm"]]),
        "odo": detect_column(numeric_cols, [["الكيلو متر", "odometer", "odo"]]),
        "total_amount": detect_column(numeric_cols, [["اجمالى المبلغ", "totalamount", "amount", "total"]]),
        "fuel": detect_column(numeric_cols, [["سولار", "fuel", "diesel", "petrol", "gas"]]),
        "garage_out": detect_column(numeric_cols, [["تحرك من الجراج", "garageout", "out"]]),
        "garage_in": detect_column(numeric_cols, [["دخول الى الجراج", "garagein", "in"]]),
        "cost_per_km": detect_column(numeric_cols, [["تكلفه الكيلو", "costperkm"]]),
        "km_per_liter": detect_column(numeric_cols, [["عدد الكيلو فى اللتر", "kmperl", "kmpl"]]),
        "notes": detect_column(cols, [["اخرى", "other", "note", "description"]]),
    }


def build_metrics(df: pd.DataFrame, schema: dict[str, str | None]) -> pd.DataFrame:
    data = df.copy()

    if schema["daily_km"]:
        data["__daily_km"] = safe_numeric(data[schema["daily_km"]])
    if schema["fuel"]:
        data["__fuel"] = safe_numeric(data[schema["fuel"]])
    if schema["total_amount"]:
        data["__cost"] = safe_numeric(data[schema["total_amount"]])
    if schema["garage_out"]:
        data["__garage_out"] = safe_numeric(data[schema["garage_out"]])
    if schema["garage_in"]:
        data["__garage_in"] = safe_numeric(data[schema["garage_in"]])
    if schema["odo"]:
        data["__odo"] = safe_numeric(data[schema["odo"]])

    if "__daily_km" in data.columns and "__fuel" in data.columns:
        data["__km_per_liter"] = data["__daily_km"] / data["__fuel"].replace(0, pd.NA)
    elif schema["km_per_liter"] and schema["km_per_liter"] in data.columns:
        data["__km_per_liter"] = safe_numeric(data[schema["km_per_liter"]])

    if "__daily_km" in data.columns and "__cost" in data.columns:
        data["__cost_per_km"] = data["__cost"] / data["__daily_km"].replace(0, pd.NA)
    elif schema["cost_per_km"] and schema["cost_per_km"] in data.columns:
        data["__cost_per_km"] = safe_numeric(data[schema["cost_per_km"]])

    if "__garage_out" in data.columns and "__garage_in" in data.columns:
        data["__garage_gap"] = data["__garage_in"] - data["__garage_out"]

    if schema["date"] and schema["date"] in data.columns:
        data["__date"] = safe_date(data[schema["date"]])
    else:
        data["__date"] = pd.NaT

    data["__month"] = data["__date"].dt.to_period("M").astype(str)
    data["__day"] = data["__date"].dt.date.astype("string")
    return data


def median_value(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.median())


def score_suspicious_rows(df: pd.DataFrame, schema: dict[str, str | None]) -> pd.DataFrame:
    scored = df.copy()
    scored["__risk_score"] = 0.0
    scored["__risk_notes"] = ""

    if "__km_per_liter" in scored.columns:
        med = median_value(scored["__km_per_liter"])
        if med:
            mask = scored["__km_per_liter"] < med * 0.75
            scored.loc[mask, "__risk_score"] += 40
            scored.loc[mask, "__risk_notes"] += f"km/L below 75% of median ({med:.2f}); "

    if "__cost_per_km" in scored.columns:
        med = median_value(scored["__cost_per_km"])
        if med:
            mask = scored["__cost_per_km"] > med * 1.25
            scored.loc[mask, "__risk_score"] += 30
            scored.loc[mask, "__risk_notes"] += f"cost/km above 125% of median ({med:.2f}); "

    if "__daily_km" in scored.columns:
        top_cutoff = scored["__daily_km"].quantile(0.95)
        mask = scored["__daily_km"] >= top_cutoff
        scored.loc[mask, "__risk_score"] += 10
        scored.loc[mask, "__risk_notes"] += f"top 5% daily KM (>= {top_cutoff:.0f}); "

    if "__daily_km" in scored.columns:
        zero_km_mask = scored["__daily_km"].fillna(0) <= 0
        if "__fuel" in scored.columns:
            zero_km_mask &= scored["__fuel"].fillna(0) > 0
        if "__cost" in scored.columns:
            zero_km_mask |= (scored["__daily_km"].fillna(0) <= 0) & (scored["__cost"].fillna(0) > 0)
        scored.loc[zero_km_mask, "__risk_score"] += 25
        scored.loc[zero_km_mask, "__risk_notes"] += "positive fuel/cost with zero KM; "

    if schema["driver"] and schema["destination"] and "__date" in scored.columns:
        dup_mask = scored.duplicated(
            subset=[c for c in [schema["driver"], schema["destination"], "__day"] if c in scored.columns],
            keep=False,
        )
        scored.loc[dup_mask, "__risk_score"] += 15
        scored.loc[dup_mask, "__risk_notes"] += "duplicate driver-route-day pattern; "

    if "__garage_gap" in scored.columns and "__daily_km" in scored.columns:
        valid = scored["__garage_gap"].notna() & scored["__daily_km"].notna() & (scored["__daily_km"] > 0)
        mask = valid & (scored["__garage_gap"].sub(scored["__daily_km"]).abs() > scored["__daily_km"] * 0.15 + 25)
        scored.loc[mask, "__risk_score"] += 35
        scored.loc[mask, "__risk_notes"] += "garage gap does not match daily KM; "

    if schema["driver"] and schema["driver"] in scored.columns and "__km_per_liter" in scored.columns:
        driver_median = scored.groupby(schema["driver"])["__km_per_liter"].transform("median")
        mask = scored["__km_per_liter"] < driver_median * 0.8
        scored.loc[mask, "__risk_score"] += 15
        scored.loc[mask, "__risk_notes"] += "below driver median km/L; "

    if schema["destination"] and schema["destination"] in scored.columns and "__cost_per_km" in scored.columns:
        route_median = scored.groupby(schema["destination"])["__cost_per_km"].transform("median")
        mask = scored["__cost_per_km"] > route_median * 1.2
        scored.loc[mask, "__risk_score"] += 15
        scored.loc[mask, "__risk_notes"] += "above route median cost/km; "

    scored["__risk_probability"] = scored["__risk_score"].clip(upper=100)
    return scored.sort_values("__risk_score", ascending=False)


def safe_label(value: float | int | None, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    return f"{value:,}{suffix}"


def compare_drivers(filtered: pd.DataFrame, schema: dict[str, str | None]) -> pd.DataFrame | None:
    if not schema["driver"] or schema["driver"] not in filtered.columns:
        return None
    if "__daily_km" not in filtered.columns and "__fuel" not in filtered.columns and "__cost" not in filtered.columns:
        return None

    driver_df = filtered.groupby(schema["driver"], dropna=False).size().reset_index(name="trips")
    agg_map = {}
    if "__daily_km" in filtered.columns:
        agg_map["distance"] = ("__daily_km", "sum")
    if "__fuel" in filtered.columns:
        agg_map["fuel"] = ("__fuel", "sum")
    if "__cost" in filtered.columns:
        agg_map["cost"] = ("__cost", "sum")
    if "__km_per_liter" in filtered.columns:
        agg_map["median_kmpl"] = ("__km_per_liter", "median")
    if "__cost_per_km" in filtered.columns:
        agg_map["median_cost_per_km"] = ("__cost_per_km", "median")

    if agg_map:
        metric_df = filtered.groupby(schema["driver"], dropna=False).agg(**agg_map).reset_index()
        driver_df = driver_df.merge(metric_df, on=schema["driver"], how="left")

    if "distance" in driver_df.columns and "fuel" in driver_df.columns:
        driver_df["avg_kmpl"] = driver_df["distance"] / driver_df["fuel"].replace(0, pd.NA)
    elif "median_kmpl" in driver_df.columns:
        driver_df["avg_kmpl"] = driver_df["median_kmpl"]
    else:
        driver_df["avg_kmpl"] = pd.NA

    if "distance" in driver_df.columns and "cost" in driver_df.columns:
        driver_df["cost_per_km"] = driver_df["cost"] / driver_df["distance"].replace(0, pd.NA)
    elif "median_cost_per_km" in driver_df.columns:
        driver_df["cost_per_km"] = driver_df["median_cost_per_km"]
    else:
        driver_df["cost_per_km"] = pd.NA

    driver_df["risk_score"] = (
        driver_df["avg_kmpl"].rank(pct=True, ascending=True).fillna(0) * 40
        + driver_df["cost_per_km"].rank(pct=True, ascending=False).fillna(0) * 40
        + driver_df["trips"].rank(pct=True, ascending=False).fillna(0) * 20
    ).fillna(0)

    return driver_df.sort_values("risk_score", ascending=False)


def comparison_summary(driver_df: pd.DataFrame, driver_a: str, driver_b: str, driver_col: str) -> pd.DataFrame:
    rows = []
    subset = driver_df[driver_df[driver_col].astype(str).isin([driver_a, driver_b])].copy()
    for _, row in subset.iterrows():
        rows.append(
            {
                "driver": row[driver_col],
                "trips": row.get("trips"),
                "distance": row.get("distance"),
                "fuel": row.get("fuel"),
                "cost": row.get("cost"),
                "avg_kmpl": row.get("avg_kmpl"),
                "cost_per_km": row.get("cost_per_km"),
                "risk_score": row.get("risk_score"),
            }
        )
    return pd.DataFrame(rows)


st.markdown(
    """
    <div class="hero">
      <h1>Fleet Control Dashboard</h1>
      <p>لوحة تحكم ديناميكية لمراقبة السائقين، مقارنة الرحلات، وكشف الشذوذ بشكل واضح للإدارة</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader("Upload CSV / Excel", type=["csv", "xlsx", "xls"])

if not uploaded_file:
    st.info("ارفع ملف Excel أو CSV علشان نبدأ.")
    st.stop()

try:
    raw_df = load_file(uploaded_file)
except Exception as exc:
    st.error(f"Failed to read file: {exc}")
    st.stop()

raw_df = normalize_columns(raw_df)
schema = detect_schema(raw_df)
df = build_metrics(raw_df, schema)
scored_df = score_suspicious_rows(df, schema)

with st.expander("Detected schema", expanded=False):
    st.json(schema)

with st.expander("Preview data", expanded=False):
    st.write("Columns:", list(raw_df.columns))
    st.dataframe(raw_df.head(20), use_container_width=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
text_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

top = st.columns(5)
with top[0]:
    st.metric("Rows", f"{len(df):,}")
with top[1]:
    st.metric("Columns", f"{len(df.columns):,}")
with top[2]:
    st.metric("Drivers", f"{df[schema['driver']].nunique():,}" if schema["driver"] else "N/A")
with top[3]:
    st.metric("Routes", f"{df[schema['destination']].nunique():,}" if schema["destination"] else "N/A")
with top[4]:
    flagged = int((scored_df["__risk_score"] >= 15).sum())
    st.metric("Flagged trips", f"{flagged:,}")

filters = st.columns(3)
filtered = df.copy()

if schema["driver"] and schema["driver"] in filtered.columns:
    with filters[0]:
        driver_choice = st.selectbox("Driver", ["All"] + sorted(filtered[schema["driver"]].dropna().astype(str).unique().tolist()))
    if driver_choice != "All":
        filtered = filtered[filtered[schema["driver"]].astype(str) == driver_choice]

if schema["destination"] and schema["destination"] in filtered.columns:
    with filters[1]:
        route_choice = st.selectbox("Route", ["All"] + sorted(filtered[schema["destination"]].dropna().astype(str).unique().tolist()))
    if route_choice != "All":
        filtered = filtered[filtered[schema["destination"]].astype(str) == route_choice]

date_col = schema["date"]
if date_col and date_col in filtered.columns:
    dates = safe_date(filtered[date_col]).dropna()
    if not dates.empty:
        with filters[2]:
            date_range = st.date_input(
                "Date range",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
            )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
            mask = safe_date(filtered[date_col]).between(pd.Timestamp(start), pd.Timestamp(end))
            filtered = filtered[mask]

tabs = st.tabs(["Executive Dashboard", "Driver Analytics", "Route Intelligence", "Suspicious Trips", "Data Explorer"])

with tabs[0]:
    st.subheader("Executive Dashboard")
    c1, c2, c3, c4, c5 = st.columns(5)
    trips = len(filtered)
    total_km = float(filtered["__daily_km"].sum()) if "__daily_km" in filtered.columns else 0.0
    total_fuel = float(filtered["__fuel"].sum()) if "__fuel" in filtered.columns else 0.0
    total_cost = float(filtered["__cost"].sum()) if "__cost" in filtered.columns else 0.0
    avg_cost_per_km = total_cost / total_km if total_km else 0.0
    avg_kmpl = total_km / total_fuel if total_fuel else 0.0

    c1.metric("Trips", f"{trips:,}", "رحلة")
    c2.metric("Total KM", f"{total_km:,.0f}", "كم")
    c3.metric("Fuel", f"{total_fuel:,.1f}", "لتر")
    c4.metric("Cost", f"{total_cost:,.0f}", "ج.م")
    c5.metric("Cost / KM", f"{avg_cost_per_km:.2f}", f"{avg_kmpl:.2f} km/L")

    chart_left, chart_right = st.columns(2)
    if "__km_per_liter" in filtered.columns:
        with chart_left:
            fig = px.histogram(
                filtered.dropna(subset=["__km_per_liter"]),
                x="__km_per_liter",
                nbins=18,
                title="Fuel efficiency distribution",
            )
            st.plotly_chart(fig, use_container_width=True)
    if "__month" in filtered.columns and filtered["__month"].notna().any():
        monthly = (
            filtered.groupby("__month", dropna=False)
            .agg(
                trips=("__month", "size"),
                km=("__daily_km", "sum") if "__daily_km" in filtered.columns else ("__month", "size"),
                fuel=("__fuel", "sum") if "__fuel" in filtered.columns else ("__month", "size"),
                cost=("__cost", "sum") if "__cost" in filtered.columns else ("__month", "size"),
            )
            .reset_index()
        )
        with chart_right:
            fig = px.line(
                monthly,
                x="__month",
                y=[col for col in ["km", "fuel", "cost"] if col in monthly.columns],
                markers=True,
                title="Monthly trend",
            )
            st.plotly_chart(fig, use_container_width=True)

    insight = []
    if schema["driver"] and "__km_per_liter" in scored_df.columns:
        driver_medians = scored_df.groupby(schema["driver"])["__km_per_liter"].median().sort_values()
        if not driver_medians.empty:
            insight.append(f"Lowest median fuel efficiency: {driver_medians.index[0]} at {driver_medians.iloc[0]:.2f} km/L.")
    if not scored_df.empty:
        top_risk = scored_df.iloc[0]
        insight.append(
            f"Highest risk trip score: {top_risk['__risk_score']:.0f} | risk probability: {top_risk['__risk_probability']:.0f}%."
        )
    if schema["driver"] and schema["driver"] in filtered.columns and schema["destination"] and schema["destination"] in filtered.columns:
        high_risk_driver = (
            scored_df.groupby(schema["driver"])["__risk_score"].mean().sort_values(ascending=False)
        )
        if not high_risk_driver.empty:
            insight.append(f"Most exposed driver by average risk: {high_risk_driver.index[0]}.")

    st.markdown('<div class="insight-box"><strong>Quick Insight</strong></div>', unsafe_allow_html=True)
    if insight:
        for item in insight:
            st.write(f"- {item}")
    else:
        st.write("- Upload a richer file to generate operational insights.")

with tabs[1]:
    st.subheader("Driver Analytics")
    driver_df = compare_drivers(filtered, schema)
    if driver_df is not None and schema["driver"]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Drivers", f"{driver_df.shape[0]:,}")
        c2.metric("Best efficiency", safe_label(driver_df["avg_kmpl"].max(), " km/L"))
        c3.metric("Worst efficiency", safe_label(driver_df["avg_kmpl"].min(), " km/L"))
        c4.metric("Top risk", safe_label(driver_df["risk_score"].max()))

        cols = [schema["driver"], "trips"]
        for extra in ["distance", "fuel", "cost", "avg_kmpl", "cost_per_km", "risk_score"]:
            if extra in driver_df.columns:
                cols.append(extra)
        st.dataframe(driver_df[cols], use_container_width=True)

        fig = px.bar(
            driver_df.head(15),
            x=schema["driver"],
            y="risk_score",
            color="avg_kmpl" if "avg_kmpl" in driver_df.columns else None,
            title="Driver risk ranking",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Driver-to-driver comparison")
        driver_choices = sorted(filtered[schema["driver"]].dropna().astype(str).unique().tolist())
        compare_cols = st.columns(2)
        with compare_cols[0]:
            driver_a = st.selectbox("Driver A", driver_choices, index=0)
        with compare_cols[1]:
            driver_b_default = 1 if len(driver_choices) > 1 else 0
            driver_b = st.selectbox("Driver B", driver_choices, index=driver_b_default)

        compare_df = comparison_summary(driver_df, driver_a, driver_b, schema["driver"])
        if not compare_df.empty:
            compare_df["driver"] = compare_df["driver"].astype(str)
            st.dataframe(compare_df, use_container_width=True)

            long_compare = compare_df.melt(id_vars="driver", var_name="metric", value_name="value")
            fig = px.bar(
                long_compare,
                x="metric",
                y="value",
                color="driver",
                barmode="group",
                title="Driver comparison",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different drivers to compare.")
    else:
        st.info("No driver or km/L data detected.")

with tabs[2]:
    st.subheader("Route Intelligence")
    if schema["destination"] and schema["destination"] in filtered.columns:
        route_df = filtered.groupby(schema["destination"], dropna=False).size().reset_index(name="trips")
        if "__daily_km" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(distance=("__daily_km", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__fuel" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(fuel=("__fuel", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__cost" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(cost=("__cost", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__km_per_liter" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(avg_kmpl=("__km_per_liter", "median")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__cost_per_km" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(avg_cost_per_km=("__cost_per_km", "median")).reset_index(),
                on=schema["destination"],
                how="left",
            )

        st.dataframe(route_df.sort_values("trips", ascending=False), use_container_width=True)

        y_col = "trips"
        for candidate in ["avg_cost_per_km", "avg_kmpl", "cost", "fuel", "distance"]:
            if candidate in route_df.columns:
                y_col = candidate
                break

        fig = px.bar(route_df.head(15), x=schema["destination"], y=y_col, title=f"Route {y_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No route column detected.")

with tabs[3]:
    st.subheader("Suspicious Trips")
    suspicious = scored_df[scored_df["__risk_score"] >= 15].copy().head(50)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Flagged trips", f"{len(suspicious):,}")
    a2.metric("Highest risk", f"{suspicious['__risk_score'].max():.0f}" if not suspicious.empty else "0")
    a3.metric(
        "Median km/L",
        f"{scored_df['__km_per_liter'].median():.2f}" if "__km_per_liter" in scored_df.columns and not scored_df["__km_per_liter"].dropna().empty else "N/A",
    )
    a4.metric(
        "Median cost/km",
        f"{scored_df['__cost_per_km'].median():.2f}" if "__cost_per_km" in scored_df.columns and not scored_df["__cost_per_km"].dropna().empty else "N/A",
    )

    if not suspicious.empty:
        risk_dist = suspicious.copy()
        risk_dist["risk_bucket"] = pd.cut(
            risk_dist["__risk_score"],
            bins=[0, 15, 35, 60, 1000],
            labels=["Low", "Medium", "High", "Critical"],
            include_lowest=True,
        )
        bucket_counts = risk_dist["risk_bucket"].value_counts().reset_index()
        bucket_counts.columns = ["bucket", "count"]
        st.plotly_chart(
            px.bar(bucket_counts, x="bucket", y="count", title="Risk bucket distribution"),
            use_container_width=True,
        )

    if not suspicious.empty:
        show_cols = []
        for col in [schema["date"], schema["driver"], schema["destination"], schema["daily_km"], schema["fuel"], schema["total_amount"], schema["garage_out"], schema["garage_in"]]:
            if col and col in suspicious.columns:
                show_cols.append(col)
        for col in ["__daily_km", "__fuel", "__cost", "__km_per_liter", "__cost_per_km", "__garage_gap", "__risk_score", "__risk_notes"]:
            if col in suspicious.columns:
                show_cols.append(col)

        st.dataframe(suspicious[show_cols], use_container_width=True)

        if schema["driver"] and schema["destination"]:
            heat = suspicious.pivot_table(
                index=schema["driver"],
                columns=schema["destination"],
                values="__risk_score",
                aggfunc="max",
                fill_value=0,
            ).reset_index()
            heat_melted = heat.melt(id_vars=schema["driver"], var_name="route", value_name="risk")
            fig = px.density_heatmap(heat_melted, x="route", y=schema["driver"], z="risk", title="Driver x Route risk heatmap")
            st.plotly_chart(fig, use_container_width=True)

        note_view = suspicious[
            [c for c in [schema["driver"], schema["destination"], "__risk_score", "__risk_notes"] if c and c in suspicious.columns]
        ].copy()
        if not note_view.empty:
            st.markdown("### Why these trips were flagged")
            st.dataframe(note_view, use_container_width=True)

        csv_buffer = io.StringIO()
        suspicious.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download suspicious trips",
            csv_buffer.getvalue(),
            file_name="suspicious_trips.csv",
            mime="text/csv",
        )
    else:
        st.success("No suspicious trips detected with the current rules.")

with tabs[4]:
    st.subheader("Data Explorer")
    st.write("Detected columns:", list(raw_df.columns))
    st.dataframe(filtered, use_container_width=True)

    csv_buffer = io.StringIO()
    filtered.to_csv(csv_buffer, index=False)
    st.download_button(
        "Download filtered data as CSV",
        csv_buffer.getvalue(),
        file_name=f"filtered_{uploaded_file.name.rsplit('.', 1)[0]}.csv",
        mime="text/csv",
    )

st.caption(f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
