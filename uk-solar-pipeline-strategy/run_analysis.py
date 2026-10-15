"""Reproduce every table and chart in this repo:  python run_analysis.py"""
from pathlib import Path

import pandas as pd

from src import analysis, charts
from src.prepare import load

OUT = Path(__file__).resolve().parent / "outputs" / "tables"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df, log = load()
    log.to_csv(OUT / "00_cleaning_log.csv", index=False)

    stage = analysis.pipeline_by_stage(df)
    apps = analysis.applications_by_year(df)
    cohort = analysis.cohort_outcomes(df)
    regions = analysis.regional_scorecard(df)
    build_time = analysis.time_to_construction(df)
    head = analysis.headline_numbers(df)

    stage.to_csv(OUT / "01_pipeline_by_stage_gw.csv")
    apps.to_csv(OUT / "02_applications_by_year_gw.csv")
    cohort.to_csv(OUT / "03_consent_cohort_outcomes.csv")
    regions.to_csv(OUT / "04_regional_scorecard.csv")
    build_time.to_csv(OUT / "05_months_consent_to_construction.csv")
    pd.Series(head).to_csv(OUT / "headline_numbers.csv", header=["value"])

    charts.pipeline_by_stage(stage)
    charts.applications_by_year(apps)
    charts.cohort_outcomes(cohort)
    charts.approval_vs_buildout(regions)
    charts.region_matrix(regions)
    charts.pipeline_map(df)

    print(log.to_string(index=False))
    print()
    for k, v in head.items():
        print(f"{k:38s} {v:,.3f}" if isinstance(v, float) else f"{k:38s} {v}")


if __name__ == "__main__":
    main()
