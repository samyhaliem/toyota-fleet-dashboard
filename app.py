import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="لوحة تحليل التشغيل والتكلفة",
    page_icon="🚚",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at top left, rgba(37,99,235,0.10), transparent 28%),
          radial-gradient(circle at top right, rgba(16,185,129,0.08), transparent 22%),
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
        return pd.to_datetime(pd.Series([pd.NaT] * len(values), index=values.index), errors="coerce")


def load_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    raise ValueError("ارفع ملف CSV أو Excel.")


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
            scored.loc[mask, "__risk_notes"] += f"كفاءة الوقود أقل من 75% من المتوسط ({med:.2f}); "

    if "__cost_per_km" in scored.columns:
        med = median_value(scored["__cost_per_km"])
        if med:
            mask = scored["__cost_per_km"] > med * 1.25
            scored.loc[mask, "__risk_score"] += 30
            scored.loc[mask, "__risk_notes"] += f"تكلفة الكيلومتر أعلى من 125% من المتوسط ({med:.2f}); "

    if "__daily_km" in scored.columns:
        top_cutoff = scored["__daily_km"].quantile(0.95)
        mask = scored["__daily_km"] >= top_cutoff
        scored.loc[mask, "__risk_score"] += 10
        scored.loc[mask, "__risk_notes"] += f"ضمن أعلى 5% من الرحلات اليومية (>= {top_cutoff:.0f}); "

    if "__daily_km" in scored.columns:
        zero_km_mask = scored["__daily_km"].fillna(0) <= 0
        if "__fuel" in scored.columns:
            zero_km_mask &= scored["__fuel"].fillna(0) > 0
        if "__cost" in scored.columns:
            zero_km_mask |= (scored["__daily_km"].fillna(0) <= 0) & (scored["__cost"].fillna(0) > 0)
        scored.loc[zero_km_mask, "__risk_score"] += 25
        scored.loc[zero_km_mask, "__risk_notes"] += "وجود وقود أو تكلفة مع كيلومترات صفر؛ "

    if schema["driver"] and schema["destination"] and "__date" in scored.columns:
        dup_mask = scored.duplicated(
            subset=[c for c in [schema["driver"], schema["destination"], "__day"] if c in scored.columns],
            keep=False,
        )
        scored.loc[dup_mask, "__risk_score"] += 15
        scored.loc[dup_mask, "__risk_notes"] += "نمط مكرر لنفس السائق والوجهة واليوم؛ "

    if "__garage_gap" in scored.columns and "__daily_km" in scored.columns:
        valid = scored["__garage_gap"].notna() & scored["__daily_km"].notna() & (scored["__daily_km"] > 0)
        mask = valid & (scored["__garage_gap"].sub(scored["__daily_km"]).abs() > scored["__daily_km"] * 0.15 + 25)
        scored.loc[mask, "__risk_score"] += 35
        scored.loc[mask, "__risk_notes"] += "فرق الجراج لا يطابق الكيلومترات اليومية؛ "

    if schema["driver"] and schema["driver"] in scored.columns and "__km_per_liter" in scored.columns:
        driver_median = scored.groupby(schema["driver"])["__km_per_liter"].transform("median")
        mask = scored["__km_per_liter"] < driver_median * 0.8
        scored.loc[mask, "__risk_score"] += 15
        scored.loc[mask, "__risk_notes"] += "أقل من متوسط السائق نفسه في كفاءة الوقود؛ "

    if schema["destination"] and schema["destination"] in scored.columns and "__cost_per_km" in scored.columns:
        route_median = scored.groupby(schema["destination"])["__cost_per_km"].transform("median")
        mask = scored["__cost_per_km"] > route_median * 1.2
        scored.loc[mask, "__risk_score"] += 15
        scored.loc[mask, "__risk_notes"] += "أعلى من متوسط الوجهة في تكلفة الكيلومتر؛ "

    scored["__risk_probability"] = scored["__risk_score"].clip(upper=100)
    return scored.sort_values("__risk_score", ascending=False)


def compare_drivers(filtered: pd.DataFrame, schema: dict[str, str | None]) -> pd.DataFrame | None:
    driver_col = schema["driver"]
    if not driver_col or driver_col not in filtered.columns:
        return None
    if "__daily_km" not in filtered.columns and "__fuel" not in filtered.columns and "__cost" not in filtered.columns:
        return None

    driver_df = filtered.groupby(driver_col, dropna=False).size().reset_index(name="trips")
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
        metric_df = filtered.groupby(driver_col, dropna=False).agg(**agg_map).reset_index()
        driver_df = driver_df.merge(metric_df, on=driver_col, how="left")

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
    subset = driver_df[driver_df[driver_col].astype(str).isin([driver_a, driver_b])].copy()
    rows = []
    for _, row in subset.iterrows():
        rows.append(
            {
                "السائق": row[driver_col],
                "عدد الرحلات": row.get("trips"),
                "إجمالي الكيلومترات": row.get("distance"),
                "إجمالي السولار": row.get("fuel"),
                "إجمالي التكلفة": row.get("cost"),
                "متوسط كم/لتر": row.get("avg_kmpl"),
                "تكلفة/كم": row.get("cost_per_km"),
                "درجة التنبيه": row.get("risk_score"),
            }
        )
    return pd.DataFrame(rows)


def safe_label(value: float | int | None, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    return f"{value:,}{suffix}"


def build_driver_compare_metrics(filtered: pd.DataFrame, schema: dict[str, str | None]) -> tuple[pd.DataFrame | None, list[str]]:
    driver_df = compare_drivers(filtered, schema)
    if driver_df is None or schema["driver"] is None:
        return None, []

    names = driver_df[schema["driver"]].dropna().astype(str).tolist()
    if len(names) < 2:
        return driver_df, names
    return driver_df, names[:2]


st.markdown(
    """
    <div class="hero">
      <h1>لوحة تحليل التشغيل والتكلفة</h1>
      <p>متابعة السائقين، مقارنة الرحلات، وتوضيح أثر الأداء على التكلفة بشكل واضح للإدارة</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader("ارفع ملف CSV أو Excel", type=["csv", "xlsx", "xls"])

if not uploaded_file:
    st.info("ارفع ملف Excel أو CSV علشان نبدأ.")
    st.stop()

try:
    raw_df = load_file(uploaded_file)
except Exception as exc:
    st.error(f"فشل قراءة الملف: {exc}")
    st.stop()

raw_df = normalize_columns(raw_df)
schema = detect_schema(raw_df)
df = build_metrics(raw_df, schema)
scored_df = score_suspicious_rows(df, schema)

with st.expander("الهيكل المكتشف", expanded=False):
    st.json(schema)

with st.expander("معاينة البيانات", expanded=False):
    st.write("الأعمدة:", list(raw_df.columns))
    st.dataframe(raw_df.head(20), use_container_width=True)

top = st.columns(5)
with top[0]:
    st.metric("عدد الصفوف", f"{len(df):,}")
with top[1]:
    st.metric("عدد الأعمدة", f"{len(df.columns):,}")
with top[2]:
    st.metric("السائقون", f"{df[schema['driver']].nunique():,}" if schema["driver"] else "N/A")
with top[3]:
    st.metric("الوجهات", f"{df[schema['destination']].nunique():,}" if schema["destination"] else "N/A")
with top[4]:
    flagged = int((scored_df["__risk_score"] >= 15).sum())
    st.metric("الرحلات تحت التحليل", f"{flagged:,}")

filters = st.columns(3)
filtered = df.copy()

if schema["driver"] and schema["driver"] in filtered.columns:
    with filters[0]:
        driver_choice = st.selectbox("السائق", ["الكل"] + sorted(filtered[schema["driver"]].dropna().astype(str).unique().tolist()))
    if driver_choice != "الكل":
        filtered = filtered[filtered[schema["driver"]].astype(str) == driver_choice]

if schema["destination"] and schema["destination"] in filtered.columns:
    with filters[1]:
        route_choice = st.selectbox("الوجهة", ["الكل"] + sorted(filtered[schema["destination"]].dropna().astype(str).unique().tolist()))
    if route_choice != "الكل":
        filtered = filtered[filtered[schema["destination"]].astype(str) == route_choice]

if schema["date"] and schema["date"] in filtered.columns:
    dates = safe_date(filtered[schema["date"]]).dropna()
    if not dates.empty:
        with filters[2]:
            date_range = st.date_input(
                "نطاق التاريخ",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
            )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
            mask = safe_date(filtered[schema["date"]]).between(pd.Timestamp(start), pd.Timestamp(end))
            filtered = filtered[mask]

tabs = st.tabs(["الملخص التنفيذي", "مقارنة الأداء", "تحليل الوجهات", "الرحلات التي تحتاج متابعة", "استكشاف البيانات"])

with tabs[0]:
    st.subheader("الملخص التنفيذي")
    c1, c2, c3, c4, c5 = st.columns(5)
    trips = len(filtered)
    total_km = float(filtered["__daily_km"].sum()) if "__daily_km" in filtered.columns else 0.0
    total_fuel = float(filtered["__fuel"].sum()) if "__fuel" in filtered.columns else 0.0
    total_cost = float(filtered["__cost"].sum()) if "__cost" in filtered.columns else 0.0
    avg_cost_per_km = total_cost / total_km if total_km else 0.0
    avg_kmpl = total_km / total_fuel if total_fuel else 0.0

    c1.metric("عدد الرحلات", f"{trips:,}", "رحلة")
    c2.metric("إجمالي الكيلومترات", f"{total_km:,.0f}", "كم")
    c3.metric("إجمالي السولار", f"{total_fuel:,.1f}", "لتر")
    c4.metric("إجمالي التكلفة", f"{total_cost:,.0f}", "ج.م")
    c5.metric("تكلفة / كم", f"{avg_cost_per_km:.2f}", f"{avg_kmpl:.2f} كم/لتر")

    chart_left, chart_right = st.columns(2)
    if schema["driver"] and "__cost" in filtered.columns:
        with chart_left:
            cost_by_driver = (
                filtered.groupby(schema["driver"], dropna=False)
                .agg(إجمالي_التكلفة=("__cost", "sum"))
                .reset_index()
                .sort_values("إجمالي_التكلفة", ascending=False)
                .head(10)
            )
            fig = px.bar(
                cost_by_driver,
                x="إجمالي_التكلفة",
                y=schema["driver"],
                orientation="h",
                title="أكثر السائقين تأثيرًا على التكلفة",
            )
            st.plotly_chart(fig, use_container_width=True)
    elif schema["destination"] and "__cost" in filtered.columns:
        with chart_left:
            cost_by_route = (
                filtered.groupby(schema["destination"], dropna=False)
                .agg(إجمالي_التكلفة=("__cost", "sum"))
                .reset_index()
                .sort_values("إجمالي_التكلفة", ascending=False)
                .head(10)
            )
            fig = px.bar(
                cost_by_route,
                x="إجمالي_التكلفة",
                y=schema["destination"],
                orientation="h",
                title="أكثر الوجهات تأثيرًا على التكلفة",
            )
            st.plotly_chart(fig, use_container_width=True)

    if "__month" in filtered.columns and filtered["__month"].notna().any():
        agg_dict = {"trips": ("__month", "size")}
        if "__daily_km" in filtered.columns:
            agg_dict["km"] = ("__daily_km", "sum")
        if "__fuel" in filtered.columns:
            agg_dict["fuel"] = ("__fuel", "sum")
        if "__cost" in filtered.columns:
            agg_dict["cost"] = ("__cost", "sum")
        monthly = filtered.groupby("__month", dropna=False).agg(**agg_dict).reset_index()
        with chart_right:
            fig = px.line(
                monthly,
                x="__month",
                y=[c for c in ["km", "fuel", "cost"] if c in monthly.columns],
                markers=True,
                title="الاتجاه الشهري للتكلفة والكميات",
            )
            st.plotly_chart(fig, use_container_width=True)

    driver_compare_df, top_two_drivers = build_driver_compare_metrics(filtered, schema)
    if driver_compare_df is not None and len(top_two_drivers) >= 2 and schema["driver"]:
        st.markdown("### مقارنة سريعة بين السائقين")
        compare_short = comparison_summary(driver_compare_df, top_two_drivers[0], top_two_drivers[1], schema["driver"])
        if not compare_short.empty:
            cols = st.columns(2)
            first = compare_short.iloc[0]
            second = compare_short.iloc[1] if len(compare_short) > 1 else None

            with cols[0]:
                st.metric("السائق الأول", first["السائق"])
                st.metric("الرحلات", safe_label(first["عدد الرحلات"]))
                st.metric("متوسط كم/لتر", safe_label(first["متوسط كم/لتر"], " كم/لتر"))
                st.metric("درجة التنبيه", safe_label(first["درجة التنبيه"]))

            if second is not None:
                with cols[1]:
                    st.metric("السائق الثاني", second["السائق"])
                    st.metric("الرحلات", safe_label(second["عدد الرحلات"]))
                    st.metric("متوسط كم/لتر", safe_label(second["متوسط كم/لتر"], " كم/لتر"))
                    st.metric("درجة التنبيه", safe_label(second["درجة التنبيه"]))

            compare_chart = compare_short.melt(id_vars="السائق", var_name="المؤشر", value_name="القيمة")
            fig = px.bar(
                compare_chart,
                x="المؤشر",
                y="القيمة",
                color="السائق",
                barmode="group",
                title="مقارنة مباشرة بين السائقين",
            )
            st.plotly_chart(fig, use_container_width=True)

            if len(compare_short) == 2:
                first = compare_short.iloc[0]
                second = compare_short.iloc[1]
                kmpl_first = pd.to_numeric(pd.Series([first["متوسط كم/لتر"]]), errors="coerce").iloc[0]
                kmpl_second = pd.to_numeric(pd.Series([second["متوسط كم/لتر"]]), errors="coerce").iloc[0]
                risk_first = pd.to_numeric(pd.Series([first["درجة التنبيه"]]), errors="coerce").iloc[0]
                risk_second = pd.to_numeric(pd.Series([second["درجة التنبيه"]]), errors="coerce").iloc[0]
                better_driver = first["السائق"] if pd.notna(kmpl_first) and pd.notna(kmpl_second) and kmpl_first >= kmpl_second else second["السائق"]
                watch_driver = first["السائق"] if pd.notna(risk_first) and pd.notna(risk_second) and risk_first >= risk_second else second["السائق"]
                st.info(f"السائق الأفضل في كفاءة الوقود حاليًا: **{better_driver}**. والسائق الذي يحتاج متابعة أكبر: **{watch_driver}**.")
                st.caption("هذه الخلاصة تساعد الإدارة على اتخاذ قرار سريع بدون قراءة الجدول كاملًا.")

    insight = []
    if schema["driver"] and "__km_per_liter" in scored_df.columns:
        driver_medians = scored_df.groupby(schema["driver"])["__km_per_liter"].median().sort_values()
        if not driver_medians.empty:
            insight.append(f"أقل كفاءة وقود ظهرت عند: {driver_medians.index[0]} بمتوسط {driver_medians.iloc[0]:.2f} كم/لتر.")
    if not scored_df.empty:
        top_risk = scored_df.iloc[0]
        insight.append(
            f"أعلى رحلة من حيث التنبيه سجلت درجة {top_risk['__risk_score']:.0f} واحتمال {top_risk['__risk_probability']:.0f}%."
        )
    if schema["driver"] and schema["destination"] and "__risk_score" in scored_df.columns:
        mean_risk = scored_df.groupby(schema["driver"])["__risk_score"].mean().sort_values(ascending=False)
        if not mean_risk.empty:
            insight.append(f"السائق الأكثر ظهورًا في التنبيهات في المتوسط: {mean_risk.index[0]}.")

    if insight:
        st.markdown("### ملخص إداري")
        for line in insight[:3]:
            st.write(f"- {line}")

    st.markdown('<div class="insight-box"><strong>ملاحظات سريعة</strong></div>', unsafe_allow_html=True)
    if insight:
        for item in insight:
            st.write(f"- {item}")
    else:
        st.write("- ارفع ملفًا يحتوي على بيانات أكثر لعرض ملاحظات تشغيلية أوضح.")

with tabs[1]:
    st.subheader("مقارنة الأداء")
    driver_df = compare_drivers(filtered, schema)
    if driver_df is not None and schema["driver"]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("عدد السائقين", f"{driver_df.shape[0]:,}")
        c2.metric("أفضل كفاءة", safe_label(driver_df["avg_kmpl"].max(), " كم/لتر"))
        c3.metric("أقل كفاءة", safe_label(driver_df["avg_kmpl"].min(), " كم/لتر"))
        c4.metric("أعلى تنبيه", safe_label(driver_df["risk_score"].max()))

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
            title="ترتيب السائقين حسب التنبيهات",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### مقارنة بين سائقين")
        driver_choices = sorted(filtered[schema["driver"]].dropna().astype(str).unique().tolist())
        compare_cols = st.columns(2)
        with compare_cols[0]:
            driver_a = st.selectbox("السائق الأول", driver_choices, index=0)
        with compare_cols[1]:
            driver_b_default = 1 if len(driver_choices) > 1 else 0
            driver_b = st.selectbox("السائق الثاني", driver_choices, index=driver_b_default)

        compare_df = comparison_summary(driver_df, driver_a, driver_b, schema["driver"])
        if not compare_df.empty:
            st.dataframe(compare_df, use_container_width=True)

            if len(compare_df) == 2:
                first = compare_df.iloc[0]
                second = compare_df.iloc[1]
                diff_kmpl = None
                diff_risk = None
                if pd.notna(first["متوسط كم/لتر"]) and pd.notna(second["متوسط كم/لتر"]):
                    diff_kmpl = float(first["متوسط كم/لتر"]) - float(second["متوسط كم/لتر"])
                if pd.notna(first["درجة التنبيه"]) and pd.notna(second["درجة التنبيه"]):
                    diff_risk = float(first["درجة التنبيه"]) - float(second["درجة التنبيه"])

                st.markdown("### الخلاصة السريعة")
                summary_lines = []
                if diff_kmpl is not None:
                    better_driver = first["السائق"] if diff_kmpl > 0 else second["السائق"]
                    summary_lines.append(f"السائق الأفضل في كفاءة الوقود هو: {better_driver}.")
                if diff_risk is not None:
                    risk_driver = first["السائق"] if diff_risk > 0 else second["السائق"]
                    summary_lines.append(f"السائق الأكثر ظهورًا في التنبيهات هو: {risk_driver}.")
                if summary_lines:
                    for line in summary_lines:
                        st.write(f"- {line}")

            long_compare = compare_df.melt(id_vars="السائق", var_name="المؤشر", value_name="القيمة")
            fig = px.bar(
                long_compare,
                x="المؤشر",
                y="القيمة",
                color="السائق",
                barmode="group",
                title="مقارنة أداء السائقين",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("اختر سائقين مختلفين للمقارنة.")
    else:
        st.info("لم يتم اكتشاف بيانات السائق أو كفاءة الوقود.")

with tabs[2]:
    st.subheader("تحليل الوجهات")
    if schema["destination"] and schema["destination"] in filtered.columns:
        route_df = filtered.groupby(schema["destination"], dropna=False).size().reset_index(name="عدد الرحلات")
        if "__daily_km" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(إجمالي_الكيلومترات=("__daily_km", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__fuel" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(إجمالي_السولار=("__fuel", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__cost" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(إجمالي_التكلفة=("__cost", "sum")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__km_per_liter" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(متوسط_كم_لتر=("__km_per_liter", "median")).reset_index(),
                on=schema["destination"],
                how="left",
            )
        if "__cost_per_km" in filtered.columns:
            route_df = route_df.merge(
                filtered.groupby(schema["destination"], dropna=False).agg(متوسط_تكلفة_كم=("__cost_per_km", "median")).reset_index(),
                on=schema["destination"],
                how="left",
            )

        st.dataframe(route_df.sort_values("عدد الرحلات", ascending=False), use_container_width=True)

        y_col = "عدد الرحلات"
        for candidate in ["متوسط_تكلفة_كم", "متوسط_كم_لتر", "إجمالي_التكلفة", "إجمالي_السولار", "إجمالي_الكيلومترات"]:
            if candidate in route_df.columns:
                y_col = candidate
                break

        fig = px.bar(
            route_df.head(15),
            x=schema["destination"],
            y=y_col,
            title=f"تحليل الوجهات حسب {y_col}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لم يتم اكتشاف عمود الوجهة.")

with tabs[3]:
    st.subheader("الرحلات التي تحتاج متابعة")
    suspicious = scored_df[scored_df["__risk_score"] >= 15].copy().head(50)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("الرحلات التي تحتاج متابعة", f"{len(suspicious):,}")
    a2.metric("أعلى تنبيه", f"{suspicious['__risk_score'].max():.0f}" if not suspicious.empty else "0")
    a3.metric(
        "وسيط كم/لتر",
        f"{scored_df['__km_per_liter'].median():.2f}" if "__km_per_liter" in scored_df.columns and not scored_df["__km_per_liter"].dropna().empty else "N/A",
    )
    a4.metric(
        "وسيط تكلفة/كم",
        f"{scored_df['__cost_per_km'].median():.2f}" if "__cost_per_km" in scored_df.columns and not scored_df["__cost_per_km"].dropna().empty else "N/A",
    )

    if not suspicious.empty:
        if schema["driver"] and schema["driver"] in suspicious.columns:
            by_driver = suspicious.groupby(schema["driver"]).size().sort_values(ascending=True).reset_index(name="عدد التنبيهات")
            by_driver = by_driver.tail(10)
            if not by_driver.empty:
                fig = px.bar(
                    by_driver,
                    x="عدد التنبيهات",
                    y=schema["driver"],
                    orientation="h",
                    title="أكثر السائقين ظهورًا في التنبيهات",
                )
                st.plotly_chart(fig, use_container_width=True)

        if schema["destination"] and schema["destination"] in suspicious.columns:
            by_route = suspicious.groupby(schema["destination"]).size().sort_values(ascending=True).reset_index(name="عدد التنبيهات")
            by_route = by_route.tail(10)
            if not by_route.empty:
                fig = px.bar(
                    by_route,
                    x="عدد التنبيهات",
                    y=schema["destination"],
                    orientation="h",
                    title="أكثر الوجهات ظهورًا في التنبيهات",
                )
                st.plotly_chart(fig, use_container_width=True)

        show_cols = []
        for col in [schema["date"], schema["driver"], schema["destination"], schema["daily_km"], schema["fuel"], schema["total_amount"], schema["garage_out"], schema["garage_in"]]:
            if col and col in suspicious.columns:
                show_cols.append(col)
        for col in ["__daily_km", "__fuel", "__cost", "__km_per_liter", "__cost_per_km", "__garage_gap", "__risk_score", "__risk_notes"]:
            if col in suspicious.columns:
                show_cols.append(col)

        st.dataframe(suspicious[show_cols], use_container_width=True)

        note_view = suspicious[
            [c for c in [schema["driver"], schema["destination"], "__risk_score", "__risk_notes"] if c and c in suspicious.columns]
        ].copy()
        if not note_view.empty:
            st.markdown("### لماذا ظهرت هذه الرحلات في قائمة التحليل")
            st.dataframe(note_view, use_container_width=True)

        csv_buffer = io.StringIO()
        suspicious.to_csv(csv_buffer, index=False)
        st.download_button(
            "تحميل الرحلات التي تحتاج متابعة",
            csv_buffer.getvalue(),
            file_name="suspicious_trips.csv",
            mime="text/csv",
        )
    else:
        st.success("لم تظهر رحلات تحتاج متابعة بالقواعد الحالية.")

with tabs[4]:
    st.subheader("استكشاف البيانات")
    st.write("الأعمدة المكتشفة:", list(raw_df.columns))
    st.dataframe(filtered, use_container_width=True)

    csv_buffer = io.StringIO()
    filtered.to_csv(csv_buffer, index=False)
    st.download_button(
        "تحميل البيانات المفلترة",
        csv_buffer.getvalue(),
        file_name=f"filtered_{uploaded_file.name.rsplit('.', 1)[0]}.csv",
        mime="text/csv",
    )

st.caption(f"تم التوليد في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
