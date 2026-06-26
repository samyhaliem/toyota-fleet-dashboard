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
            fig = px.line(monthly, x="__month", y=[col for col in ["km", "fuel", "cost"] if col in monthly.columns], markers=True, title="Monthly trend")
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
    a3.metric("Median km/L", f"{scored_df['__km_per_liter'].median():.2f}" if "__km_per_liter" in scored_df.columns and not scored_df["__km_per_liter"].dropna().empty else "N/A")
    a4.metric("Median cost/km", f"{scored_df['__cost_per_km'].median():.2f}" if "__cost_per_km" in scored_df.columns and not scored_df["__cost_per_km"].dropna().empty else "N/A")

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

        note_view = suspicious[[c for c in [schema["driver"], schema["destination"], "__risk_score", "__risk_notes"] if c and c in suspicious.columns]].copy()
        if not note_view.empty:
