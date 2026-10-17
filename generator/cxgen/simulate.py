"""Simulate six months of a telesales + support operation.

The output is a set of raw tables shaped like exports from ten different source
systems, with the defects real exports have. Ground truth (which records belong
to the same person, whether an issue was really resolved) is kept separately in
`truth_*` tables so the warehouse logic can be tested against it.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from . import config as C
from .people import make_people, messy_email, messy_phone, typo_email
from .timeutil import add_open_minutes, from_local, next_open, to_local

OLD_CODES = {
    "no_answer": "NA", "voicemail": "VM", "not_interested": "CT", "callback": "CB",
    "sale": "SALE", "dnc": "DNC", "bad_number": "BAD",
}
NEW_CODES = {
    "no_answer": "NO_ANSWER", "voicemail": "VOICEMAIL", "not_interested": "NOT_INTERESTED",
    "callback": "CALLBACK", "sale": "SOLD", "dnc": "DO_NOT_CALL", "bad_number": "BAD_NUMBER",
}

PLANS = [("Fiber 300", 55.0), ("Fiber 500", 70.0), ("Fiber 1 Gig", 85.0)]


@dataclass
class Agent:
    agent_id: str
    name: str
    site: str
    role: str  # sales | support
    skill: float
    hire_date: date
    term_date: date | None
    tier: int
    supervisor_id: str
    changes: list  # (effective_date, tier, supervisor_id, status)

    def active_on(self, d: date) -> bool:
        return self.hire_date <= d and (self.term_date is None or d < self.term_date)

    def tier_on(self, d: date) -> int:
        tier = self.changes[0][1]
        for eff, t, _sup, _st in self.changes:
            if eff <= d:
                tier = t
        return tier


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


class Simulator:
    def __init__(self, opts: C.GeneratorOptions):
        self.opts = opts
        self.rng = np.random.default_rng(opts.seed)
        self.scale = opts.scale
        self.tables: dict[str, list[dict]] = defaultdict(list)
        self.ids = defaultdict(int)

    def next_id(self, prefix: str, width: int = 7) -> str:
        self.ids[prefix] += 1
        return f"{prefix}{self.ids[prefix]:0{width}d}"

    def uniform_ts(self, d: date, start_hour: float = 0, end_hour: float = 24) -> datetime:
        seconds = self.rng.uniform(start_hour * 3600, end_hour * 3600)
        return datetime(d.year, d.month, d.day) + timedelta(seconds=float(seconds))

    # ------------------------------------------------------------------ agents
    def build_agents(self) -> None:
        rng = self.rng
        self.agents: list[Agent] = []
        self.supervisors: dict[str, list[str]] = {}
        n = 0
        from .people import FIRST_NAMES, LAST_NAMES
        for site in C.SITES:
            sups = [f"SUP-{site.name[:3].upper()}-{i + 1:02d}" for i in range(site.supervisors)]
            self.supervisors[site.name] = sups
            for role, count in (("sales", site.sales_agents), ("support", site.support_agents)):
                for _ in range(max(4, int(round(count * max(self.scale, 0.35))))):
                    n += 1
                    skill = float(rng.normal())
                    tier = 1 if skill < -0.4 else (2 if skill < 0.8 else 3)
                    hire = C.START - timedelta(days=int(rng.integers(30, 1200)))
                    self.agents.append(Agent(
                        agent_id=f"AG-{1000 + n}",
                        name=f"{FIRST_NAMES[rng.integers(len(FIRST_NAMES))]} {LAST_NAMES[rng.integers(len(LAST_NAMES))]}",
                        site=site.name, role=role, skill=skill, hire_date=hire, term_date=None,
                        tier=tier, supervisor_id=sups[rng.integers(len(sups))], changes=[],
                    ))
        # Three weak sales performers, so the coaching analysis has something real to find.
        sales = [a for a in self.agents if a.role == "sales"]
        for a in rng.choice(sales, size=3, replace=False):
            a.skill = -2.2
            a.tier = 1
        # Roster history: promotions, supervisor moves, attrition with replacement hires.
        extra: list[Agent] = []
        for a in self.agents:
            a.changes.append((a.hire_date, a.tier, a.supervisor_id, "active"))
            if rng.random() < 0.18 and a.tier < 3:
                eff = C.START + timedelta(days=int(rng.integers(20, 160)))
                a.changes.append((eff, a.tier + 1, a.changes[-1][2], "active"))
            if rng.random() < 0.10:
                eff = C.START + timedelta(days=int(rng.integers(20, 170)))
                sups = self.supervisors[a.site]
                new_sup = sups[rng.integers(len(sups))]
                a.changes.append((eff, a.tier_on(eff), new_sup, "active"))
            if rng.random() < 0.11:
                term = C.START + timedelta(days=int(rng.integers(15, 170)))
                a.term_date = term
                a.changes.append((term, a.tier_on(term), a.changes[-1][2], "terminated"))
                n += 1
                hire = term + timedelta(days=int(rng.integers(3, 20)))
                if hire <= C.END:
                    sups = self.supervisors[a.site]
                    sup = sups[rng.integers(len(sups))]
                    new = Agent(
                        agent_id=f"AG-{1000 + n}",
                        name=f"{FIRST_NAMES[rng.integers(len(FIRST_NAMES))]} {LAST_NAMES[rng.integers(len(LAST_NAMES))]}",
                        site=a.site, role=a.role, skill=float(rng.normal(-0.6, 0.6)), hire_date=hire,
                        term_date=None, tier=1, supervisor_id=sup, changes=[(hire, 1, sup, "active")],
                    )
                    extra.append(new)
            a.changes.sort(key=lambda c: c[0])
        self.agents.extend(extra)
        for a in self.agents:
            for eff, tier, sup, status in a.changes:
                self.tables["hr__agent_roster_changes"].append({
                    "agent_id": a.agent_id, "agent_name": a.name, "site": a.site, "role": a.role,
                    "tier": tier, "supervisor_id": sup, "status": status,
                    "effective_date": eff, "hire_date": a.hire_date,
                })

    def active_agents(self, d: date, role: str, site: str | None = None) -> list[Agent]:
        return [a for a in self.agents if a.role == role and a.active_on(d) and (site is None or a.site == site)]

    def agent_factor(self, a: Agent, d: date) -> float:
        tenure_days = (d - a.hire_date).days
        ramp = 0.8 if tenure_days < 90 else 1.0
        return float(np.clip(1.0 + 0.18 * a.skill, 0.45, 1.5)) * ramp

    # ------------------------------------------------------------------ people
    def build_people(self) -> None:
        days = (C.END - C.START).days + 1
        n_leads_est = int(C.LEADS_PER_DAY * days * self.scale)
        n_existing = int(C.EXISTING_CUSTOMERS * self.scale)
        self.people = make_people(self.rng, n_leads_est + n_existing + 50, C.STATES)
        self.person_cursor = 0

    def take_person(self) -> dict:
        p = self.people[self.person_cursor]
        self.person_cursor += 1
        return p

    # --------------------------------------------------------------- customers
    def build_existing_customers(self) -> None:
        self.customers: list[dict] = []
        for _ in range(int(C.EXISTING_CUSTOMERS * self.scale)):
            p = self.take_person()
            start = date(2023, 1, 1) + timedelta(days=int(self.rng.integers(0, 730)))
            self.add_subscription(p, datetime(start.year, start.month, start.day) + timedelta(hours=int(self.rng.integers(13, 23))))

    def add_subscription(self, person: dict, started_at: datetime) -> dict:
        plan, mrr = PLANS[self.rng.integers(len(PLANS))]
        email = person["email"]
        phone = person["phone"]
        if self.rng.random() < 0.03:  # billing holds a newer phone number than the lead did
            phone = f"{self.rng.integers(201, 990)}{self.rng.integers(200, 999)}{self.rng.integers(0, 10000):04d}"
            person["alt_phone"] = phone
        sub = {
            "subscription_id": self.next_id("SUB-"),
            "account_id": self.next_id("ACCT-"),
            "person_id": person["person_id"],
            "email": messy_email(self.rng, email),
            "phone": messy_phone(self.rng, phone),
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "state": person["state"],
            "plan_name": plan,
            "mrr_usd": mrr,
            "started_at": started_at,
            "cancelled_at": None,
            "cancel_reason": None,
            "_person": person,
        }
        self.customers.append(sub)
        return sub

    # ------------------------------------------------------------------- leads
    def vendor_quality(self, vendor: C.LeadVendor, d: date) -> float:
        if vendor.degrade_after and d >= vendor.degrade_after:
            return vendor.degrade_factor
        return 1.0

    def build_leads(self) -> None:
        rng = self.rng
        vendors = C.LEAD_VENDORS
        shares = np.array([v.share for v in vendors])
        shares = shares / shares.sum()
        self.lead_records: list[dict] = []
        for d in _daterange(C.START, C.END):
            weekday_mult = 1.15 if d.weekday() < 5 else 0.7
            for _ in range(rng.poisson(C.LEADS_PER_DAY * self.scale * weekday_mult)):
                vendor = vendors[rng.choice(len(vendors), p=shares)]
                if self.person_cursor >= len(self.people):
                    break
                p = self.take_person()
                local = self.uniform_ts(d, 7, 23)
                created_utc = from_local(local, p["timezone"])
                is_test = rng.random() < C.TEST_LEAD_RATE
                rec = self.make_lead(p, vendor, created_utc, is_test=is_test, is_dup=False)
                if is_test:
                    continue
                if rng.random() < C.DUPLICATE_LEAD_RATE:
                    later = created_utc + timedelta(hours=float(rng.uniform(1, 72)))
                    self.make_lead(p, vendor, later, is_test=False, is_dup=True, original=rec)
                if rng.random() < C.CROSS_VENDOR_DUP_RATE:
                    other = vendors[rng.integers(len(vendors))]
                    later = created_utc + timedelta(days=float(rng.uniform(0.5, 10)))
                    if later.date() <= C.END:
                        self.make_lead(p, other, later, is_test=False, is_dup=True, original=rec)

    def make_lead(self, p: dict, vendor: C.LeadVendor, created_utc: datetime, *, is_test: bool,
                  is_dup: bool, original: dict | None = None) -> dict:
        rng = self.rng
        lead_id = self.next_id("00Q", 9)
        local = to_local(created_utc, p["timezone"])
        first, last, email = p["first_name"], p["last_name"], p["email"]
        if is_test:
            first, last = "TEST", "Lead"
            email = f"qa+{lead_id.lower()}@test.northwind.example"
        elif rng.random() < 0.02:
            email = typo_email(rng, email)  # web-form typo; the phone still links the person
        rec = {
            "lead_id": lead_id,
            "vendor_name": vendor.name,
            "campaign_name": C.CAMPAIGNS[rng.integers(len(C.CAMPAIGNS))],
            "first_name": first,
            "last_name": last,
            "email": messy_email(rng, email),
            "phone": messy_phone(rng, p["phone"]),
            "state": p["state"],
            "created_at_local": local,
            "created_timezone": p["timezone"],
            "lead_status": "Open",
            "_person": p,
            "_vendor": vendor,
            "_created_utc": created_utc,
            "_is_test": is_test,
            "_is_dup": is_dup,
        }
        self.lead_records.append(rec)
        self.tables["truth__lead_person"].append({
            "lead_id": lead_id, "person_id": p["person_id"], "is_test": is_test, "is_duplicate": is_dup,
        })
        return rec

    # ------------------------------------------------------------------ dialer
    def simulate_dialing(self) -> None:
        rng = self.rng
        self.sold_people: set[str] = set()
        self.contacted_people: set[str] = set()
        for rec in sorted(self.lead_records, key=lambda r: r["_created_utc"]):
            if rec["_is_test"]:
                continue
            created = rec["_created_utc"]
            d = created.date()
            vendor: C.LeadVendor = rec["_vendor"]
            person = rec["_person"]
            site = "Tampa" if rng.random() < 0.55 else "Phoenix"
            pool = self.active_agents(d, "sales", site) or self.active_agents(d, "sales")
            agent = pool[rng.integers(len(pool))]
            # Speed to lead, in open (business) minutes.
            start = next_open(created)
            local_hour_site = to_local(start, "America/Phoenix" if site == "Phoenix" else "America/New_York").hour
            median = 6.0
            if site == "Phoenix" and 11 <= local_hour_site < 14:
                median = 75.0  # lunch-hour staffing gap at Phoenix
            elif to_local(start, "America/New_York").weekday() == 0:
                median = 16.0  # Monday backlog
            delay = float(rng.lognormal(math.log(median), 0.6))
            attempt_ts = add_open_minutes(start, delay)
            quality = self.vendor_quality(vendor, d)
            speed_factor = 1.30 if delay <= 5 else (1.0 if delay <= 30 else (0.78 if delay <= 60 else 0.62))
            contact_decay = 1.0 if delay <= 5 else (0.9 if delay <= 30 else (0.78 if delay <= 60 else 0.68))
            already = person["person_id"] in self.contacted_people
            sold = False
            qualified = False
            contacted = False
            for attempt_no in range(1, C.MAX_ATTEMPTS + 1):
                if attempt_ts.date() > C.END:
                    break
                p_contact = 0.24 * vendor.contact_mult * (quality ** 0.5) * (contact_decay if attempt_no == 1 else 0.75)
                outcome: str
                r = rng.random()
                if r < 0.015:
                    outcome = "bad_number"
                elif r < 0.015 + p_contact:
                    contacted = True
                    p_qual = 0.42 * quality if not already else 0.15
                    qualified = qualified or (rng.random() < p_qual)
                    p_sale = C.BASE_SALE_PROB * vendor.sale_mult * quality * speed_factor * self.agent_factor(agent, attempt_ts.date())
                    if qualified and not already and person["person_id"] not in self.sold_people and rng.random() < min(p_sale, 0.95):
                        outcome = "sale"
                    elif rng.random() < 0.012:
                        outcome = "dnc"
                    elif rng.random() < 0.35:
                        outcome = "callback"
                    else:
                        outcome = "not_interested"
                else:
                    outcome = "voicemail" if rng.random() < 0.45 else "no_answer"
                self.emit_attempt(rec, agent, attempt_ts, attempt_no, outcome)
                if outcome == "sale":
                    sold = True
                    self.sold_people.add(person["person_id"])
                    break
                if outcome in ("bad_number", "dnc") or (outcome == "not_interested" and rng.random() < 0.8):
                    break
                gap_hours = float(rng.uniform(2, 30)) if outcome != "callback" else float(rng.uniform(20, 50))
                attempt_ts = next_open(attempt_ts + timedelta(hours=gap_hours))
                if attempt_no == 1:
                    # Some agents abandon the cadence after the first attempt (contact strategy breach).
                    if rng.random() < 0.12:
                        break
            if contacted:
                self.contacted_people.add(person["person_id"])
            rec["_sold"] = sold
            rec["_qualified"] = qualified
            rec["_agent"] = agent
            rec["lead_status"] = "Converted" if sold else ("Working" if contacted else "Unreached")
            if qualified:
                opp_created = rec.get("_first_contact_ts", created)
                opp = {
                    "opportunity_id": self.next_id("006", 9),
                    "lead_id": rec["lead_id"],
                    "owner_agent_id": agent.agent_id,
                    "created_at": opp_created,
                    "stage_name": "Closed Won" if sold else "Closed Lost",
                    "close_date": (rec["_sale_ts"] if sold else opp_created + timedelta(days=int(rng.integers(1, 15)))).date(),
                    "amount_usd": None,
                }
                if sold:
                    plan, mrr = PLANS[rng.integers(len(PLANS))]
                    opp["amount_usd"] = round(mrr * 12, 2)
                    opp["plan_name"] = plan
                self.tables["crm__opportunities"].append(opp)
                if sold and rng.random() > vendor.no_activation_rate:
                    act = rec["_sale_ts"] + timedelta(days=float(rng.uniform(2, 10)))
                    if act.date() <= C.END:
                        sub = self.add_subscription(person, act)
                        sub["_activated_from_lead"] = rec["lead_id"]

    def emit_attempt(self, rec: dict, agent: Agent, ts: datetime, attempt_no: int, outcome: str) -> None:
        rng = self.rng
        codes = OLD_CODES if ts.date() < C.DISPOSITION_RENAME_DATE else NEW_CODES
        connected = outcome in ("sale", "not_interested", "callback", "dnc")
        ring = int(rng.integers(8, 35))
        if connected:
            talk = int(rng.lognormal(math.log(1100 if outcome == "sale" else 330), 0.45))
            hold = int(rng.integers(0, 180)) if rng.random() < 0.4 else 0
            wrap = int(rng.integers(30, 120))
            rec.setdefault("_first_contact_ts", ts)
        else:
            talk = int(rng.integers(15, 40)) if outcome == "voicemail" else 0
            hold, wrap = 0, int(rng.integers(5, 25))
        if outcome == "sale":
            rec["_sale_ts"] = ts
        loaded = ts + timedelta(minutes=float(rng.uniform(5, 90)))
        if rng.random() < C.LATE_ARRIVAL_RATE:
            loaded = ts + timedelta(days=float(rng.uniform(1, 5)))
        self.tables["dialer__call_attempts"].append({
            "attempt_id": self.next_id("CA-", 8),
            "lead_id": rec["lead_id"],
            "dialed_number": messy_phone(rng, rec["_person"]["phone"]),
            "agent_id": agent.agent_id,
            "campaign_name": rec["campaign_name"],
            "attempt_number": attempt_no,
            "started_at_utc": ts,
            "ring_seconds": ring,
            "talk_seconds": talk,
            "hold_seconds": hold,
            "wrap_seconds": wrap,
            "disposition_code": codes[outcome],
            "_loaded_at": loaded,
        })
        if outcome == "sale":
            rec["_sold_attempt"] = attempt_no

    # ----------------------------------------------------------------- support
    def simulate_support(self) -> None:
        rng = self.rng
        intents = C.INTENTS
        weights = np.array([i.weight for i in intents])
        weights = weights / weights.sum()
        order_idx = [k for k, i in enumerate(intents) if i.l1 == "Orders"]
        period_start = datetime(C.START.year, C.START.month, C.START.day)
        period_end = datetime(C.END.year, C.END.month, C.END.day) + timedelta(days=1)
        for sub in list(self.customers):
            start = max(sub["started_at"], period_start)
            if start >= period_end:
                continue
            months_active = (period_end - start).days / 30.4
            # Base churn draw for the period (independent of service experience).
            if rng.random() < 1 - (1 - C.BASE_MONTHLY_CHURN) ** months_active:
                when = start + timedelta(days=float(rng.uniform(0, (period_end - start).days)))
                self.cancel(sub, when, "Moving / price")
            n_episodes = rng.poisson(C.EPISODES_PER_CUSTOMER_MONTH * months_active * (1.6 if sub["started_at"] >= period_start else 1.0))
            for _ in range(n_episodes):
                ts = start + timedelta(seconds=float(rng.uniform(0, (period_end - start).total_seconds())))
                if sub["cancelled_at"] is not None and ts >= sub["cancelled_at"]:
                    continue
                new_customer = (ts - sub["started_at"]).days < 30
                if new_customer and rng.random() < 0.5:
                    k = order_idx[rng.integers(len(order_idx))]
                else:
                    k = int(rng.choice(len(intents), p=weights))
                self.run_episode(sub, intents[k], ts, period_end)

    def cancel(self, sub: dict, when: datetime, reason: str) -> None:
        if sub["cancelled_at"] is None or when < sub["cancelled_at"]:
            sub["cancelled_at"] = when
            sub["cancel_reason"] = reason

    def run_episode(self, sub: dict, intent: C.Intent, ts: datetime, period_end: datetime) -> None:
        rng = self.rng
        episode_id = self.next_id("EP-", 7)
        person = sub["_person"]
        resolved = False
        contacts = 0
        first_channel = "chat" if rng.random() < C.DIGITAL_SHARE else "voice"
        channel = first_channel
        bot_contained_unresolved = False
        while contacts < 4 and ts < period_end:
            if sub["cancelled_at"] is not None and ts >= sub["cancelled_at"]:
                break
            contacts += 1
            if channel == "chat":
                resolved, escalated, contained = self.bot_session(sub, intent, ts, episode_id, contacts)
                if contained and not resolved:
                    bot_contained_unresolved = True
            else:
                resolved = self.voice_contact(sub, intent, ts, episode_id, contacts)
            if resolved:
                break
            # Not resolved: does the customer try again?
            p_retry = 0.72 if contacts == 1 else 0.5
            if rng.random() > p_retry:
                break
            ts = ts + timedelta(hours=float(rng.uniform(4, 6 * 24)))
            channel = "voice" if rng.random() < 0.75 else "chat"
        if not resolved:
            if rng.random() < 0.22:
                created = ts + timedelta(hours=float(rng.uniform(1, 30)))
                if created < period_end:
                    self.tables["ticketing__tickets"].append({
                        "ticket_id": self.next_id("TK-", 7),
                        "requester_email": messy_email(rng, person["email"]),
                        "subject_category": intent.code,
                        "created_at": created,
                        "status": "solved" if rng.random() < 0.6 else "open",
                        "solved_at": created + timedelta(days=float(rng.uniform(1, 6))) if rng.random() < 0.6 else None,
                    })
            if rng.random() < intent.churn_if_unresolved * (1.3 if bot_contained_unresolved else 1.0):
                self.cancel(sub, ts + timedelta(days=float(rng.uniform(1, 30))), "Service experience")
        elif intent.code == "ACC_CANCEL" and rng.random() < 0.55:
            # "Resolved" for a cancel request often means the cancellation was processed.
            self.cancel(sub, ts + timedelta(days=float(rng.uniform(0, 3))), "Requested cancellation")
        self.tables["truth__episodes"].append({
            "episode_id": episode_id, "person_id": person["person_id"], "account_id": sub["account_id"],
            "intent_code": intent.code, "first_channel": first_channel, "contacts": contacts,
            "truly_resolved": resolved,
        })

    def bot_session(self, sub: dict, intent: C.Intent, ts: datetime, episode_id: str, contact_no: int):
        rng = self.rng
        session_id = self.next_id("SES-", 8)
        person = sub["_person"]
        bot_seconds = int(rng.integers(60, 420))
        escalated = rng.random() < intent.bot_escalate
        contained = not escalated
        resolved = contained and rng.random() < intent.bot_resolve
        nlu_intent = intent.code if rng.random() < 0.93 else "UNKNOWN"
        self.tables["ccaas__interaction_legs"].append({
            "leg_id": self.next_id("LEG-", 8), "session_id": session_id, "leg_sequence": 1,
            "channel": "chat_bot", "queue_name": "Virtual Assistant", "agent_id": None,
            "customer_phone": None, "customer_email": messy_email(rng, person["email"]),
            "started_at": ts, "ended_at": ts + timedelta(seconds=bot_seconds),
            "talk_seconds": bot_seconds, "hold_seconds": 0, "wrap_seconds": 0,
            "abandoned": False, "transferred": escalated, "bot_contained": contained,
            "agent_marked_resolved": None, "intent_code": nlu_intent,
        })
        self.tables["truth__session_episode"].append({"session_id": session_id, "episode_id": episode_id, "contact_no": contact_no})
        if escalated:
            resolved = self.agent_leg(sub, intent, ts + timedelta(seconds=bot_seconds + int(rng.integers(30, 600))),
                                      session_id, 2, "chat_agent", email=person["email"])
        return resolved, escalated, contained

    def voice_contact(self, sub: dict, intent: C.Intent, ts: datetime, episode_id: str, contact_no: int) -> bool:
        rng = self.rng
        session_id = self.next_id("SES-", 8)
        self.tables["truth__session_episode"].append({"session_id": session_id, "episode_id": episode_id, "contact_no": contact_no})
        phone = sub["_person"].get("alt_phone", sub["_person"]["phone"])
        if rng.random() < 0.06:  # abandoned in queue
            wait = int(rng.integers(60, 600))
            self.tables["ccaas__interaction_legs"].append({
                "leg_id": self.next_id("LEG-", 8), "session_id": session_id, "leg_sequence": 1,
                "channel": "voice", "queue_name": self.queue_for(intent), "agent_id": None,
                "customer_phone": messy_phone(rng, phone), "customer_email": None,
                "started_at": ts, "ended_at": ts + timedelta(seconds=wait),
                "talk_seconds": 0, "hold_seconds": 0, "wrap_seconds": 0,
                "abandoned": True, "transferred": False, "bot_contained": None,
                "agent_marked_resolved": None, "intent_code": None,
            })
            return False
        return self.agent_leg(sub, intent, ts, session_id, 1, "voice", phone=phone)

    def queue_for(self, intent: C.Intent) -> str:
        return {"Billing": "Billing", "Technical": "Tech Support", "Orders": "Orders"}.get(intent.l1, "General Care")

    def agent_leg(self, sub: dict, intent: C.Intent, ts: datetime, session_id: str, seq: int, channel: str,
                  phone: str | None = None, email: str | None = None) -> bool:
        rng = self.rng
        d = ts.date()
        pool = self.active_agents(d, "support") or [a for a in self.agents if a.role == "support"]
        agent = pool[rng.integers(len(pool))]
        p_transfer = 0.22 if intent.l1 in ("Billing", "Technical") else 0.10
        transfer = seq < 3 and rng.random() < p_transfer
        talk = int(rng.lognormal(math.log(intent.aht_s * 0.75), 0.4))
        hold = int(rng.integers(0, 240)) if rng.random() < 0.45 else 0
        wrap = int(rng.integers(20, 110))
        p_resolve = min(0.97, intent.human_resolve * 0.86 * self.agent_factor(agent, d))
        resolved = (not transfer) and rng.random() < p_resolve
        # Agents mark "resolved" generously; this is what the legacy FCR counts.
        marked = None if transfer else (resolved or rng.random() < 0.6)
        self.tables["ccaas__interaction_legs"].append({
            "leg_id": self.next_id("LEG-", 8), "session_id": session_id, "leg_sequence": seq,
            "channel": channel, "queue_name": self.queue_for(intent), "agent_id": agent.agent_id,
            "customer_phone": messy_phone(rng, phone) if phone else None,
            "customer_email": messy_email(rng, email) if email else None,
            "started_at": ts, "ended_at": ts + timedelta(seconds=talk + hold),
            "talk_seconds": talk, "hold_seconds": hold, "wrap_seconds": wrap,
            "abandoned": False, "transferred": transfer, "bot_contained": None,
            "agent_marked_resolved": marked,
            "intent_code": intent.code if rng.random() < 0.95 else "OTHER",
        })
        self.qa_maybe(agent, self.tables["ccaas__interaction_legs"][-1])
        if transfer:
            return self.agent_leg(sub, intent, ts + timedelta(seconds=talk + hold + int(rng.integers(20, 240))),
                                  session_id, seq + 1, channel, phone=phone, email=email)
        return resolved

    def qa_maybe(self, agent: Agent, leg: dict) -> None:
        rng = self.rng
        if rng.random() >= C.QA_SAMPLE_RATE:
            return
        base = 78 + 7 * agent.skill
        self.tables["qa__evaluations"].append({
            "evaluation_id": self.next_id("QA-", 6),
            "leg_id": leg["leg_id"],
            "agent_id": agent.agent_id,
            "evaluated_at": leg["ended_at"] + timedelta(days=float(rng.uniform(1, 6))),
            "knowledge_score": int(np.clip(rng.normal(base, 8), 20, 100)),
            "compliance_score": int(np.clip(rng.normal(90, 6), 40, 100)),
            "soft_skills_score": int(np.clip(rng.normal(base + 3, 7), 20, 100)),
        })

    # --------------------------------------------------------------------- wfm
    def build_wfm(self) -> None:
        rng = self.rng
        for a in self.agents:
            off_day = int(rng.integers(0, 6))
            for d in _daterange(C.START, C.END):
                if not a.active_on(d) or d.weekday() == 6 or d.weekday() == off_day:
                    continue
                scheduled = 480
                adherence = float(np.clip(rng.normal(0.92, 0.035), 0.6, 1.0))
                if a.site == "Phoenix" and a.role == "sales":
                    adherence -= 0.09  # lunch breaks taken together; drives the speed-to-lead gap
                self.tables["wfm__agent_daily"].append({
                    "agent_id": a.agent_id, "work_date": d, "scheduled_minutes": scheduled,
                    "adherent_minutes": int(scheduled * adherence), "paid_hours": 8.0,
                    "loaded_hourly_rate_usd": C.LOADED_RATE_BY_TIER[a.tier_on(d)],
                })

    # ------------------------------------------------------------- marketing
    def build_spend(self) -> None:
        counts: dict[tuple, int] = defaultdict(int)
        for rec in self.lead_records:
            if rec["_is_test"]:
                continue
            counts[(to_local(rec["_created_utc"], "America/New_York").date(), rec["_vendor"].name, rec["campaign_name"])] += 1
        vendors = {v.name: v for v in C.LEAD_VENDORS}
        for (d, vendor, campaign), n in sorted(counts.items()):
            if d > C.END or vendors[vendor].cost_per_lead == 0:
                continue
            self.tables["marketing__vendor_spend"].append({
                "spend_date": d, "vendor_name": vendor, "campaign_name": campaign,
                "billed_leads": n, "spend_usd": round(n * vendors[vendor].cost_per_lead, 2),
            })

    # -------------------------------------------------------------- finalize
    def finalize(self) -> dict[str, pd.DataFrame]:
        for rec in self.lead_records:
            row = {k: v for k, v in rec.items() if not k.startswith("_")}
            self.tables["crm__leads"].append(row)
        for sub in self.customers:
            self.tables["billing__subscriptions"].append({k: v for k, v in sub.items() if not k.startswith("_") and k != "person_id"})
            self.tables["truth__account_person"].append({"account_id": sub["account_id"], "person_id": sub["person_id"]})
        frames = {name: pd.DataFrame(rows) for name, rows in self.tables.items()}
        frames["crm__opportunities"] = frames["crm__opportunities"].drop(columns=[c for c in ["plan_name"] if c in frames["crm__opportunities"].columns])
        return frames

    def run(self) -> dict[str, pd.DataFrame]:
        self.build_agents()
        self.build_people()
        self.build_existing_customers()
        self.build_leads()
        self.simulate_dialing()
        self.simulate_support()
        self.build_wfm()
        self.build_spend()
        return self.finalize()


def simulate(opts: C.GeneratorOptions | None = None) -> dict[str, pd.DataFrame]:
    return Simulator(opts or C.GeneratorOptions()).run()
