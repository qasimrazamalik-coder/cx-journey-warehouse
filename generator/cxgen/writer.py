"""Load simulated source extracts into DuckDB, one schema per source system."""

from __future__ import annotations

import pandas as pd

from .legacy import legacy_monthly_kpis

EVENT_RESULT = {
    "NA": "no_answer", "NO_ANSWER": "no_answer", "VM": "voicemail", "VOICEMAIL": "voicemail",
    "CT": "not_interested", "NOT_INTERESTED": "not_interested", "CB": "callback", "CALLBACK": "callback",
    "SALE": "sold", "SOLD": "sold", "DNC": "do_not_call", "DO_NOT_CALL": "do_not_call",
    "BAD": "bad_number", "BAD_NUMBER": "bad_number",
}


def to_events_format(attempts: pd.DataFrame) -> pd.DataFrame:
    """A second dialer vendor's export: different names, epoch seconds, durations in milliseconds."""
    started = pd.to_datetime(attempts["started_at_utc"])
    return pd.DataFrame({
        "call_id": attempts["attempt_id"].str.replace("CA-", "EVT-", regex=False),
        "crm_lead_ref": attempts["lead_id"],
        "to_number": attempts["dialed_number"],
        "user_id": attempts["agent_id"],
        "list_name": attempts["campaign_name"],
        "seq": attempts["attempt_number"],
        "start_epoch": (started - pd.Timestamp("1970-01-01")).dt.total_seconds().round().astype("int64"),
        "ring_ms": attempts["ring_seconds"] * 1000,
        "talk_ms": attempts["talk_seconds"] * 1000,
        "hold_ms": attempts["hold_seconds"] * 1000,
        "acw_ms": attempts["wrap_seconds"] * 1000,
        "result": attempts["disposition_code"].map(EVENT_RESULT),
        "_loaded_at": attempts["_loaded_at"],
    })


def write_duckdb(frames: dict[str, pd.DataFrame], db_path: str, dialer_format: str = "classic") -> dict[str, int]:
    import duckdb

    frames = dict(frames)
    frames["legacy_bi__monthly_kpis"] = legacy_monthly_kpis(frames)
    if dialer_format == "events":
        frames["dialer__call_events"] = to_events_format(frames.pop("dialer__call_attempts"))
    elif dialer_format != "classic":
        raise ValueError(f"unknown dialer_format {dialer_format!r}")

    counts: dict[str, int] = {}
    con = duckdb.connect(db_path)
    try:
        existing = con.execute(
            "select schema_name from information_schema.schemata where schema_name like 'raw_%'"
        ).fetchall()
        for (schema,) in existing:
            con.execute(f'drop schema "{schema}" cascade')
        for key, df in sorted(frames.items()):
            system, table = key.split("__", 1)
            schema = f"raw_{system}"
            con.execute(f'create schema if not exists "{schema}"')
            con.register("_frame", df)
            con.execute(f'create table "{schema}"."{table}" as select * from _frame')
            con.unregister("_frame")
            counts[f"{schema}.{table}"] = len(df)
    finally:
        con.close()
    return counts
