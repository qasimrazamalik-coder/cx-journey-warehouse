"""Identity resolution: link records from every system into one customer_key.

Grain: one row per (record_type, record_id).

Method: records are joined into connected components through shared normalised
emails and phones (union-find). A phone number seen with more than
MAX_EMAILS_PER_PHONE distinct emails is treated as shared (a business line, a
family phone) and is not used as a link, to avoid merging different people.

Accuracy against the simulation's ground truth is checked by the test
assert_identity_resolution_accuracy.
"""

import hashlib

import pandas as pd

MAX_EMAILS_PER_PHONE = 3


def model(dbt, session):
    dbt.config(materialized="table")
    records = dbt.ref("int_identity__records").df()

    emails_per_phone = (
        records.dropna(subset=["phone", "email"]).groupby("phone")["email"].nunique()
    )
    shared_phones = set(emails_per_phone[emails_per_phone > MAX_EMAILS_PER_PHONE].index)

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    rec_nodes = []
    for rtype, rid, email, phone in records[["record_type", "record_id", "email", "phone"]].itertuples(index=False):
        node = f"r:{rtype}:{rid}"
        find(node)
        if isinstance(email, str):
            union(node, f"e:{email}")
        if isinstance(phone, str) and phone not in shared_phones:
            union(node, f"p:{phone}")
        rec_nodes.append((rtype, rid, node))

    # Component key = hash of the smallest identifier node in the component (stable across runs).
    roots = {}
    for node in list(parent):
        if node.startswith(("e:", "p:")):
            r = find(node)
            if r not in roots or node < roots[r]:
                roots[r] = node

    rows = []
    for rtype, rid, node in rec_nodes:
        r = find(node)
        anchor = roots.get(r, node)
        key = "cust_" + hashlib.md5(anchor.encode()).hexdigest()[:16]
        rows.append((rtype, rid, key))
    return pd.DataFrame(rows, columns=["record_type", "record_id", "customer_key"])
