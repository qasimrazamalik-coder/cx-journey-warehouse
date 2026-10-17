"""Simulation settings for Northwind Connect, a fictional broadband provider.

Every number here is an assumption chosen to make the data behave like a real
telesales + support operation. None of it describes a real company.
"""

from dataclasses import dataclass, field
from datetime import date

SEED = 20260117

START = date(2025, 1, 1)
END = date(2025, 6, 30)  # inclusive

# Contact center opening hours, in US Eastern time.
OPEN_HOUR_ET = 8
CLOSE_HOUR_ET = 20
OPEN_WEEKDAYS = {0, 1, 2, 3, 4, 5}  # Mon-Sat

STATES = {
    # state: (timezone, weight)
    "NY": ("America/New_York", 0.13),
    "FL": ("America/New_York", 0.14),
    "GA": ("America/New_York", 0.08),
    "OH": ("America/New_York", 0.07),
    "TX": ("America/Chicago", 0.15),
    "IL": ("America/Chicago", 0.08),
    "CO": ("America/Denver", 0.06),
    "AZ": ("America/Phoenix", 0.07),
    "CA": ("America/Los_Angeles", 0.15),
    "WA": ("America/Los_Angeles", 0.07),
}


@dataclass(frozen=True)
class LeadVendor:
    name: str
    share: float  # share of lead volume
    cost_per_lead: float  # USD
    contact_mult: float  # multiplier on base contact probability
    sale_mult: float  # multiplier on base sale probability once contacted
    no_activation_rate: float  # share of sales that never activate
    degrade_after: date | None = None  # quality drops after this date
    degrade_factor: float = 1.0


LEAD_VENDORS = [
    LeadVendor("BrightPath Leads", 0.24, 38.0, 1.05, 1.10, 0.08),
    LeadVendor("Summit Digital", 0.20, 42.0, 1.10, 1.15, 0.07),
    # Cheapest per lead and the biggest by volume. Quality falls after mid-March.
    LeadVendor("Clickstream Media", 0.30, 19.0, 0.95, 0.85, 0.15,
               degrade_after=date(2025, 3, 15), degrade_factor=0.5),
    LeadVendor("Harbor Referral Network", 0.12, 55.0, 1.25, 1.30, 0.05),
    LeadVendor("Organic Web Form", 0.14, 0.0, 1.15, 1.05, 0.06),
]

CAMPAIGNS = ["Q1 Acquisition", "Spring Speed Promo", "Win-back", "Fiber Launch"]

LEADS_PER_DAY = 230
DUPLICATE_LEAD_RATE = 0.11  # a vendor resubmits the same person
CROSS_VENDOR_DUP_RATE = 0.04  # the same person arrives via a second vendor
TEST_LEAD_RATE = 0.006

BASE_CONTACT_PROB = 0.62
BASE_SALE_PROB = 0.27
MAX_ATTEMPTS = 6  # playbook: up to 6 attempts

# Disposition codes were renamed by the dialer vendor on this date (schema drift).
DISPOSITION_RENAME_DATE = date(2025, 4, 1)

EXISTING_CUSTOMERS = 14000

# Support demand: contact episodes per active customer per month.
EPISODES_PER_CUSTOMER_MONTH = 0.17
BOT_SHARE_OF_DIGITAL = 1.0  # every chat starts with the bot
DIGITAL_SHARE = 0.58  # share of episodes that start in chat (bot) vs voice


@dataclass(frozen=True)
class Intent:
    l1: str
    l2: str
    l3: str
    code: str
    weight: float
    bot_resolve: float  # probability the bot truly resolves it
    bot_escalate: float  # probability the customer asks for an agent in-session
    human_resolve: float  # base probability a human resolves on first contact
    aht_s: int  # typical human handle seconds
    churn_if_unresolved: float  # 30-day cancellation probability when left unresolved


INTENTS = [
    Intent("Account", "Access", "Password reset", "ACC_PWD_RESET", 0.10, 0.92, 0.04, 0.95, 240, 0.01),
    Intent("Account", "Profile", "Update address", "ACC_ADDR", 0.04, 0.78, 0.10, 0.94, 300, 0.01),
    Intent("Account", "Plan", "Upgrade plan", "ACC_UPGRADE", 0.05, 0.55, 0.30, 0.90, 480, 0.02),
    Intent("Account", "Plan", "Downgrade plan", "ACC_DOWNGRADE", 0.04, 0.40, 0.25, 0.85, 540, 0.10),
    Intent("Account", "Cancellation", "Cancel service", "ACC_CANCEL", 0.04, 0.30, 0.45, 0.70, 660, 0.45),
    Intent("Billing", "Payment", "Update card", "BIL_CARD", 0.07, 0.82, 0.08, 0.96, 260, 0.02),
    Intent("Billing", "Unexpected charge", "Proration after plan change", "BIL_PRORATION", 0.08, 0.25, 0.12, 0.78, 600, 0.14),
    Intent("Billing", "Refund", "Refund status", "BIL_REFUND", 0.06, 0.35, 0.10, 0.82, 420, 0.12),
    Intent("Billing", "Dispute", "Charge dispute", "BIL_DISPUTE", 0.05, 0.20, 0.15, 0.72, 720, 0.18),
    Intent("Technical", "Connectivity", "Outage", "TEC_OUTAGE", 0.09, 0.50, 0.20, 0.80, 540, 0.08),
    Intent("Technical", "Speed", "Slow speed", "TEC_SLOW", 0.08, 0.30, 0.18, 0.74, 780, 0.11),
    Intent("Technical", "Equipment", "Router setup", "TEC_ROUTER", 0.07, 0.45, 0.22, 0.83, 660, 0.04),
    Intent("Orders", "Install", "Install status", "ORD_INSTALL_STATUS", 0.07, 0.86, 0.05, 0.95, 240, 0.02),
    Intent("Orders", "Install", "Reschedule install", "ORD_RESCHEDULE", 0.05, 0.60, 0.15, 0.92, 360, 0.04),
    Intent("Orders", "Delivery", "Equipment delivery status", "ORD_DELIVERY", 0.05, 0.85, 0.05, 0.95, 220, 0.02),
    Intent("General", "Info", "Coverage check", "GEN_COVERAGE", 0.06, 0.90, 0.04, 0.96, 200, 0.00),
]

BASE_MONTHLY_CHURN = 0.012


@dataclass(frozen=True)
class Site:
    name: str
    timezone: str
    sales_agents: int
    support_agents: int
    supervisors: int


SITES = [
    Site("Tampa", "America/New_York", 34, 46, 6),
    Site("Phoenix", "America/Phoenix", 26, 34, 5),
]

# Loaded hourly cost per agent tier, USD (assumption, used for cost to serve).
LOADED_RATE_BY_TIER = {1: 27.0, 2: 31.0, 3: 36.0}
QA_SAMPLE_RATE = 0.05
LATE_ARRIVAL_RATE = 0.02  # share of dialer rows loaded days after the event


@dataclass(frozen=True)
class GeneratorOptions:
    seed: int = SEED
    dialer_format: str = "classic"  # "classic" (client A) or "events" (client B)
    scale: float = 1.0  # multiply volumes, e.g. 0.1 for fast CI runs
    extra: dict = field(default_factory=dict)
