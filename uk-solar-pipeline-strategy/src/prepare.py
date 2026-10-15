"""Load and clean the Renewable Energy Planning Database (REPD).

Scope: utility-scale solar PV and battery storage, 1 MW and above, Great Britain and
Northern Ireland (offshore excluded). Every cleaning decision is logged so it can be
explained and challenged.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "REPD_Publication_Q2_2026.csv"
DATA_CUTOFF = pd.Timestamp("2026-07-24")  # latest 'Record Last Updated' in this extract

DATE_COLS = {
    "Planning Application Submitted": "submitted",
    "Planning Application Withdrawn": "withdrawn",
    "Planning Permission Refused": "refused",
    "Appeal Lodged": "appeal_lodged",
    "Appeal Refused": "appeal_refused",
    "Appeal Granted": "appeal_granted",
    "Planning Permission Granted": "granted",
    "Under Construction": "construction_start",
    "Operational": "operational",
}

TECH = {"Solar Photovoltaics": "Solar", "Battery": "Battery"}

# Development Status (short) -> pipeline stage used throughout the analysis
STAGE = {
    "Application Submitted": "In planning",
    "Appeal Lodged": "In planning",
    "Awaiting Construction": "Consented, not built",
    "Under Construction": "Under construction",
    "Operational": "Operational",
    "Application Refused": "Refused",
    "Appeal Refused": "Refused",
    "Application Withdrawn": "Withdrawn or abandoned",
    "Appeal Withdrawn": "Withdrawn or abandoned",
    "Abandoned": "Withdrawn or abandoned",
    "Planning Permission Expired": "Consent expired",
    "Decommissioned": "Decommissioned",
    "No Application Required": "No application required",
    "Revised": "Revised (superseded)",
}


def load(min_mw: float = 1.0):
    log = []
    df = pd.read_csv(RAW, encoding="latin1", low_memory=False)
    df.columns = [" ".join(c.split()) for c in df.columns]  # e.g. 'Planning Permission  Granted'
    log.append(("Rows in REPD extract", len(df)))

    df = df[df["Technology Type"].isin(TECH)].copy()
    df["tech"] = df["Technology Type"].map(TECH)
    log.append(("Solar PV and battery records", len(df)))

    for col in ["Region", "Country", "Development Status (short)", "Mounting Type for Solar"]:
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    df["mw"] = pd.to_numeric(df["Installed Capacity (MWelec)"].astype(str)
                             .str.replace(",", "").str.strip(), errors="coerce")
    log.append(("Dropped: capacity blank or not a number", int(df["mw"].isna().sum())))
    df = df[df["mw"].notna()]

    revised = df["Development Status (short)"].eq("Revised")
    log.append(("Dropped: 'Revised' records superseded by a newer application (avoids double counting)",
                int(revised.sum())))
    df = df[~revised]

    small = df["mw"] < min_mw
    log.append((f"Dropped: below {min_mw:g} MW (REPD threshold fell from 1 MW to 150 kW in 2021, "
                "so smaller projects are only consistently recorded from 2021)", int(small.sum())))
    df = df[~small]

    offshore = (df["Region"].eq("Offshore") | df["Region"].isna()).fillna(True)
    log.append(("Dropped: offshore or region missing", int(offshore.sum())))
    df = df[~offshore]

    for raw_col, new in DATE_COLS.items():
        df[new] = pd.to_datetime(df[raw_col], dayfirst=True, errors="coerce")
    future = (df[list(DATE_COLS.values())] > DATA_CUTOFF).any(axis=1)
    log.append(("Flagged: at least one event date after the extract date (likely data entry error)",
                int(future.sum())))
    df["future_date_flag"] = future

    df["stage"] = df["Development Status (short)"].map(STAGE).fillna("Other")

    # Planning outcome, counting appeals as part of the same application
    granted_any = df["granted"].notna() | df["appeal_granted"].notna() | df["stage"].isin(
        ["Consented, not built", "Under construction", "Operational", "Consent expired"])
    refused_final = df["stage"].eq("Refused")
    df["outcome"] = np.select(
        [granted_any, refused_final, df["stage"].eq("Withdrawn or abandoned") & df["granted"].isna(),
         df["stage"].eq("In planning")],
        ["Granted", "Refused", "Withdrawn", "Pending"], default="Other")

    first_decision = df[["granted", "refused"]].min(axis=1)
    df["weeks_to_decision"] = (first_decision - df["submitted"]).dt.days / 7
    bad_dur = df["weeks_to_decision"] < 0
    log.append(("Flagged: decision dated before submission (duration set to blank)", int(bad_dur.sum())))
    df.loc[bad_dur, "weeks_to_decision"] = np.nan

    df["submitted_year"] = df["submitted"].dt.year
    df["granted_year"] = df["granted"].dt.year
    log.append(("Final analysis set (projects)", len(df)))
    return df.reset_index(drop=True), pd.DataFrame(log, columns=["step", "records"])
