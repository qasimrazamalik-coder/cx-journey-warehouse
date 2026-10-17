"""People, identifiers and the messy ways source systems record them."""

from __future__ import annotations

import numpy as np

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Carlos", "Karen", "Daniel", "Lisa", "Matthew", "Nancy",
    "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley", "Steven", "Kimberly",
    "Andrew", "Emily", "Paul", "Donna", "Joshua", "Michelle", "Kenneth", "Carol",
    "Kevin", "Amanda", "Brian", "Melissa", "Aisha", "Deborah", "Omar", "Stephanie",
    "Luis", "Rebecca", "Wei", "Laura", "Priya", "Sharon", "Diego", "Cynthia",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Khan", "Patel", "Chen", "Kim", "Okafor", "Silva",
]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "aol.com", "hotmail.com"]


def make_people(rng: np.random.Generator, n: int, states: dict) -> list[dict]:
    """Ground-truth people. Each has one canonical email and phone."""
    codes = list(states)
    weights = np.array([states[c][1] for c in codes])
    weights = weights / weights.sum()
    people = []
    used_emails: set[str] = set()
    used_phones: set[str] = set()
    for i in range(n):
        first = FIRST_NAMES[rng.integers(len(FIRST_NAMES))]
        last = LAST_NAMES[rng.integers(len(LAST_NAMES))]
        state = codes[rng.choice(len(codes), p=weights)]
        while True:
            suffix = int(rng.integers(1, 9999))
            email = f"{first}.{last}{suffix}@{EMAIL_DOMAINS[rng.integers(len(EMAIL_DOMAINS))]}".lower()
            if email not in used_emails:
                used_emails.add(email)
                break
        while True:
            phone = f"{rng.integers(201, 990)}{rng.integers(200, 999)}{rng.integers(0, 10000):04d}"
            if phone not in used_phones:
                used_phones.add(phone)
                break
        people.append({
            "person_id": f"P{i + 1:06d}",
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "state": state,
            "timezone": states[state][0],
        })
    for i in range(1, len(people)):
        if rng.random() < 0.004:
            people[i]["phone"] = people[i - 1]["phone"]  # shared household phone
    return people


def typo_email(rng: np.random.Generator, email: str) -> str:
    """A mistyped address: two adjacent characters of the local part swapped."""
    local, domain = email.split("@")
    if len(local) < 4:
        return email
    i = int(rng.integers(1, len(local) - 2))
    return f"{local[:i]}{local[i + 1]}{local[i]}{local[i + 2:]}@{domain}"


def messy_phone(rng: np.random.Generator, phone: str) -> str:
    """The same 10-digit number, the way different systems format it."""
    style = rng.integers(5)
    a, b, c = phone[:3], phone[3:6], phone[6:]
    if style == 0:
        return f"({a}) {b}-{c}"
    if style == 1:
        return f"{a}.{b}.{c}"
    if style == 2:
        return f"+1{phone}"
    if style == 3:
        return f"1-{a}-{b}-{c}"
    return phone


def messy_email(rng: np.random.Generator, email: str) -> str:
    """Upper/mixed case and stray whitespace, as typed into web forms."""
    style = rng.integers(6)
    if style == 0:
        return email.upper()
    if style == 1:
        local, domain = email.split("@")
        return f"{local.title()}@{domain}"
    if style == 2:
        return f" {email} "
    return email
