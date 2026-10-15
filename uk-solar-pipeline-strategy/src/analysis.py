"""Metrics behind the recommendation. Each function answers one question."""
import pandas as pd

BUILT = ["Operational", "Under construction"]
PIPELINE_STAGES = ["In planning", "Consented, not built", "Under construction", "Operational"]
COHORT = (2019, 2022)          # consents old enough (3.5+ years) to have had a fair chance to build
DECISION_WINDOW = (2021, 2024)  # applications recent but mostly decided by mid-2026
MIN_CONSENTS = 20              # regions with fewer consents in the cohort are excluded from ranking


def pipeline_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Q1. How big is the pipeline, and where does capacity sit today? (GW)"""
    t = (df[df["stage"].isin(PIPELINE_STAGES)]
         .pivot_table(index="stage", columns="tech", values="mw", aggfunc="sum", fill_value=0) / 1000)
    t = t.reindex(PIPELINE_STAGES)
    t["Total"] = t.sum(axis=1)
    return t.round(1)


def applications_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Q2. How fast is new demand for consents growing? (GW submitted per year)"""
    t = (df[df["submitted_year"].between(2015, 2025)]
         .pivot_table(index="submitted_year", columns="tech", values="mw", aggfunc="sum", fill_value=0) / 1000)
    t.index = t.index.astype(int)
    return t.round(1)


def cohort_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Q3. Of projects consented 2019-2022, what has happened to them since? (share of projects)"""
    c = df[df["granted_year"].between(*COHORT)].copy()
    c["status_now"] = c["stage"].replace({
        "Withdrawn or abandoned": "Expired or abandoned", "Consent expired": "Expired or abandoned"})
    keep = ["Operational", "Under construction", "Consented, not built", "Expired or abandoned"]
    t = pd.crosstab(c["granted_year"].astype(int), c["status_now"], normalize="index")[keep]
    t["projects"] = c.groupby(c["granted_year"].astype(int)).size()
    return t.round(3)


def regional_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    """Q4. Which regions are easy to consent in, and which are easy to build in?"""
    apps = df[df["submitted_year"].between(*DECISION_WINDOW)]
    decided = apps[apps["outcome"].isin(["Granted", "Refused"])]
    cohort = df[df["granted_year"].between(*COHORT)]
    waiting = df[df["stage"] == "Consented, not built"]

    s = pd.DataFrame({
        "applications_2021_24": apps.groupby("Region").size(),
        "gw_applied_2021_24": apps.groupby("Region")["mw"].sum() / 1000,
        "approval_rate": decided.groupby("Region")["outcome"].apply(lambda x: (x == "Granted").mean()),
        "median_weeks_to_decision": apps.groupby("Region")["weeks_to_decision"].median(),
        "consents_2019_22": cohort.groupby("Region").size(),
        "build_out_rate": cohort.groupby("Region")["stage"].apply(lambda x: x.isin(BUILT).mean()),
        "gw_consented_not_built": waiting.groupby("Region")["mw"].sum() / 1000,
        "gw_stalled_consented_by_2022": waiting[waiting["granted_year"] <= COHORT[1]]
        .groupby("Region")["mw"].sum() / 1000,
    }).fillna({"gw_stalled_consented_by_2022": 0})
    lo, hi = wilson(s["build_out_rate"] * s["consents_2019_22"], s["consents_2019_22"])
    s["build_out_ci_low"], s["build_out_ci_high"] = lo, hi
    s["ranked"] = s["consents_2019_22"] >= MIN_CONSENTS
    ranked = s[s["ranked"]]
    # Approval rates sit in a narrow 92-99% band, so they do not separate regions.
    # The matrix therefore uses deliverability (build-out) against market depth (GW applied).
    b_mid, m_mid = ranked["build_out_rate"].median(), ranked["gw_applied_2021_24"].median()

    def quadrant(r):
        if not r["ranked"]:
            return "Too few consents to rank"
        deliverable, deep = r["build_out_rate"] >= b_mid, r["gw_applied_2021_24"] >= m_mid
        return {(True, True): "Go now", (True, False): "Selective niche",
                (False, True): "Crowded: grid-first only",
                (False, False): "Deprioritise"}[(deliverable, deep)]

    s["quadrant"] = s.apply(quadrant, axis=1)
    s.attrs["build_median"], s.attrs["market_median"] = b_mid, m_mid
    return s.sort_values("build_out_rate", ascending=False).round(3)


def wilson(successes, n, z: float = 1.645):
    """90% Wilson score interval for a proportion (robust for small samples)."""
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z ** 2 / (4 * n ** 2)) ** 0.5) / denom
    return centre - half, centre + half


def time_to_construction(df: pd.DataFrame) -> pd.DataFrame:
    """Q5. For projects that did start building, how long after consent? (months, median)"""
    st = df[df["construction_start"].notna() & df["granted"].notna()].copy()
    st["months"] = (st["construction_start"] - st["granted"]).dt.days / 30.44
    st = st[st["months"] >= 0]
    return st.groupby("tech")["months"].agg(["median", "count"]).round(1)


def headline_numbers(df: pd.DataFrame) -> dict:
    p = pipeline_by_stage(df)["Total"]
    cohort = df[df["granted_year"].between(*COHORT)]
    decided = df[df["submitted_year"].between(*DECISION_WINDOW) & df["outcome"].isin(["Granted", "Refused"])]
    waiting = df[df["stage"] == "Consented, not built"]
    stalled = waiting[waiting["granted_year"] <= COHORT[1]]
    return {
        "gw_operational": p["Operational"],
        "gw_under_construction": p["Under construction"],
        "gw_consented_not_built": p["Consented, not built"],
        "gw_in_planning": p["In planning"],
        "approval_rate_2021_24": (decided["outcome"] == "Granted").mean(),
        "cohort_build_out_rate": cohort["stage"].isin(BUILT).mean(),
        "cohort_size": len(cohort),
        "gw_stalled": stalled["mw"].sum() / 1000,
        "gw_stalled_solar": stalled.loc[stalled["tech"] == "Solar", "mw"].sum() / 1000,
        "n_stalled": len(stalled),
        "battery_share_consented_not_built": waiting.loc[waiting["tech"] == "Battery", "mw"].sum() / waiting["mw"].sum(),
    }
