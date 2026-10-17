"""Tests for the source-data simulator. Run with: pytest -q"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generator"))

from cxgen.config import GeneratorOptions  # noqa: E402
from cxgen.legacy import legacy_monthly_kpis  # noqa: E402
from cxgen.simulate import simulate  # noqa: E402
from cxgen.timeutil import add_open_minutes, is_open, next_open  # noqa: E402
from cxgen.writer import to_events_format  # noqa: E402


@pytest.fixture(scope="module")
def frames():
    return simulate(GeneratorOptions(scale=0.08))


def test_is_deterministic():
    a = simulate(GeneratorOptions(scale=0.03))
    b = simulate(GeneratorOptions(scale=0.03))
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_all_source_systems_present(frames):
    expected = {
        "crm__leads", "crm__opportunities", "dialer__call_attempts", "ccaas__interaction_legs",
        "ticketing__tickets", "billing__subscriptions", "hr__agent_roster_changes", "wfm__agent_daily",
        "qa__evaluations", "marketing__vendor_spend",
    }
    assert expected <= set(frames)


def test_planted_mess_exists(frames):
    leads = frames["crm__leads"]
    truth = frames["truth__lead_person"]
    assert truth["is_duplicate"].mean() > 0.05, "vendor resubmissions should exist"
    assert truth["is_test"].sum() > 0, "test leads should exist"
    assert leads["phone"].str.contains(r"[()\.\-+]").any(), "phones should arrive in mixed formats"
    assert (leads["email"] != leads["email"].str.strip().str.lower()).any(), "emails should arrive in mixed case"
    codes = set(frames["dialer__call_attempts"]["disposition_code"])
    assert {"SALE", "SOLD"} <= codes, "disposition codes should be renamed mid-period"


def test_ids_unique(frames):
    for table, key in [("crm__leads", "lead_id"), ("dialer__call_attempts", "attempt_id"),
                       ("ccaas__interaction_legs", "leg_id"), ("billing__subscriptions", "account_id")]:
        assert frames[table][key].is_unique, f"{table}.{key} must be unique"


def test_legacy_report_reproduces_its_known_bugs(frames):
    legacy = legacy_monthly_kpis(frames)
    assert len(legacy) == 6
    april_onward = legacy[pd.to_datetime(legacy["month"]) >= "2025-04-01"]
    assert (april_onward["contact_rate"] == 0).all(), "legacy contact rate must break after the code rename"


def test_events_format_converts_units(frames):
    events = to_events_format(frames["dialer__call_attempts"])
    src = frames["dialer__call_attempts"]
    assert (events["talk_ms"] == src["talk_seconds"] * 1000).all()
    assert events["result"].notna().all()


def test_business_hours():
    from datetime import datetime
    sunday_noon_utc = datetime(2025, 1, 12, 17, 0)
    assert not is_open(sunday_noon_utc)
    assert next_open(sunday_noon_utc) == datetime(2025, 1, 13, 13, 0)  # Monday 08:00 ET
    friday_1950_et = datetime(2025, 1, 11, 0, 50)
    # 10 open minutes Friday, then Saturday opens 08:00 ET: +5 minutes -> 08:05 ET.
    assert add_open_minutes(friday_1950_et, 15) == datetime(2025, 1, 11, 13, 5)
