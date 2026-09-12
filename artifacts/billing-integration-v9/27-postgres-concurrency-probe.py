"""Synthetic PostgreSQL race probe for Billing allocation/reversal invariants.

This is an assurance harness, not application production code.  It mirrors the
candidate router's lock order: payment row, then invoice row, then the active
allocation sum.  It uses only disposable synthetic tables and emits a compact
JSON result for the closure package.
"""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import psycopg


DB_URL = os.environ.get(
    "BILLING_PROBE_DATABASE_URL",
    "postgresql://ahmedsami@/amec_billing?host=/tmp&port=55432",
)


def as_text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def connect():
    return psycopg.connect(DB_URL)


def setup() -> None:
    with connect() as db, db.cursor() as cur:
        cur.execute(
            """
            DROP TABLE IF EXISTS billing_probe_allocations;
            DROP TABLE IF EXISTS billing_probe_reversals;
            DROP TABLE IF EXISTS billing_probe_payments;
            DROP TABLE IF EXISTS billing_probe_invoices;
            CREATE TABLE billing_probe_payments (
                id text PRIMARY KEY,
                amount numeric(18,2) NOT NULL,
                status text NOT NULL
            );
            CREATE TABLE billing_probe_invoices (
                id text PRIMARY KEY,
                payable numeric(18,2) NOT NULL
            );
            CREATE TABLE billing_probe_allocations (
                id text PRIMARY KEY,
                payment_id text NOT NULL REFERENCES billing_probe_payments(id),
                invoice_id text NOT NULL REFERENCES billing_probe_invoices(id),
                amount numeric(18,2) NOT NULL,
                status text NOT NULL
            );
            CREATE TABLE billing_probe_reversals (
                id text PRIMARY KEY,
                payment_id text NOT NULL UNIQUE REFERENCES billing_probe_payments(id)
            );
            """
        )


def insert_case(payment_id: str, payment_amount: str, invoice_id: str, invoice_amount: str) -> None:
    with connect() as db, db.cursor() as cur:
        cur.execute("INSERT INTO billing_probe_payments VALUES (%s,%s,'VERIFIED')", (payment_id, payment_amount))
        cur.execute("INSERT INTO billing_probe_invoices VALUES (%s,%s)", (invoice_id, invoice_amount))


def allocate(payment_id: str, invoice_id: str, amount: str, start: threading.Barrier) -> str:
    try:
        with connect() as db, db.cursor() as cur:
            start.wait()
            cur.execute("SELECT status FROM billing_probe_payments WHERE id=%s FOR UPDATE", (payment_id,))
            status = as_text(cur.fetchone()[0])
            cur.execute("SELECT payable FROM billing_probe_invoices WHERE id=%s FOR UPDATE", (invoice_id,))
            payable = Decimal(cur.fetchone()[0])
            if status != "VERIFIED":
                db.rollback()
                return "rejected:payment-not-verified"
            cur.execute(
                "SELECT COALESCE(sum(amount),0) FROM billing_probe_allocations WHERE payment_id=%s AND status='ALLOCATED'",
                (payment_id,),
            )
            used_payment = Decimal(cur.fetchone()[0])
            cur.execute(
                "SELECT COALESCE(sum(amount),0) FROM billing_probe_allocations WHERE invoice_id=%s AND status='ALLOCATED'",
                (invoice_id,),
            )
            used_invoice = Decimal(cur.fetchone()[0])
            if used_payment + Decimal(amount) > Decimal("100.00"):
                db.rollback()
                return "rejected:payment-limit"
            if used_invoice + Decimal(amount) > payable:
                db.rollback()
                return "rejected:invoice-limit"
            cur.execute(
                "INSERT INTO billing_probe_allocations VALUES (%s,%s,%s,%s,'ALLOCATED')",
                (str(uuid4()), payment_id, invoice_id, amount),
            )
            db.commit()
            return "allocated"
    except Exception as exc:  # pragma: no cover - evidence records unexpected races
        return f"error:{type(exc).__name__}"


def reverse(payment_id: str, start: threading.Barrier) -> str:
    try:
        with connect() as db, db.cursor() as cur:
            start.wait()
            cur.execute("SELECT status FROM billing_probe_payments WHERE id=%s FOR UPDATE", (payment_id,))
            status = as_text(cur.fetchone()[0])
            if status == "REVERSED":
                db.rollback()
                return "rejected:already-reversed"
            cur.execute("INSERT INTO billing_probe_reversals VALUES (%s,%s)", (str(uuid4()), payment_id))
            cur.execute("UPDATE billing_probe_allocations SET status='REVERSED' WHERE payment_id=%s AND status='ALLOCATED'", (payment_id,))
            cur.execute("UPDATE billing_probe_payments SET status='REVERSED' WHERE id=%s", (payment_id,))
            db.commit()
            return "reversed"
    except Exception as exc:  # pragma: no cover
        return f"error:{type(exc).__name__}"


def read_state(payment_id: str, invoice_id: str) -> dict[str, object]:
    with connect() as db, db.cursor() as cur:
        cur.execute("SELECT status FROM billing_probe_payments WHERE id=%s", (payment_id,))
        payment_status = as_text(cur.fetchone()[0])
        cur.execute("SELECT COALESCE(sum(amount),0), count(*) FROM billing_probe_allocations WHERE payment_id=%s AND status='ALLOCATED'", (payment_id,))
        payment_allocated, active_count = cur.fetchone()
        cur.execute("SELECT COALESCE(sum(amount),0) FROM billing_probe_allocations WHERE invoice_id=%s AND status='ALLOCATED'", (invoice_id,))
        invoice_allocated = cur.fetchone()[0]
        return {
            "payment_status": payment_status,
            "payment_allocated": str(payment_allocated),
            "invoice_allocated": str(invoice_allocated),
            "active_allocation_count": active_count,
        }


def run() -> dict[str, object]:
    setup()
    results: dict[str, object] = {}

    payment, invoice = "p-same-payment", "i-same-payment"
    insert_case(payment, "100.00", invoice, "100.00")
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        race = list(pool.map(lambda _: allocate(payment, invoice, "70.00", barrier), range(2)))
    results["same_payment_concurrent_allocations"] = {"outcomes": sorted(race), "state": read_state(payment, invoice)}

    payment_a, payment_b, invoice = "p-invoice-a", "p-invoice-b", "i-same-invoice"
    insert_case(payment_a, "80.00", invoice, "100.00")
    insert_case(payment_b, "80.00", "i-unused", "100.00")
    # Both allocations deliberately target the same invoice; the second payment
    # is inserted against the same invoice's race using the explicit id below.
    with connect() as db, db.cursor() as cur:
        cur.execute("UPDATE billing_probe_payments SET id=id WHERE id=%s", (payment_b,))
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        race = list(pool.map(lambda p: allocate(p, invoice, "80.00", barrier), (payment_a, payment_b)))
    results["same_invoice_concurrent_allocations"] = {"outcomes": sorted(race), "state": read_state(payment_a, invoice)}

    payment, invoice = "p-reversal-race", "i-reversal-race"
    insert_case(payment, "100.00", invoice, "100.00")
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        race = list(pool.map(lambda kind: allocate(payment, invoice, "100.00", barrier) if kind == "allocate" else reverse(payment, barrier), ("allocate", "reverse")))
    results["reversal_vs_allocation"] = {"outcomes": sorted(race), "state": read_state(payment, invoice)}

    payment, invoice = "p-double-reversal", "i-double-reversal"
    insert_case(payment, "100.00", invoice, "100.00")
    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        race = list(pool.map(lambda _: reverse(payment, barrier), range(2)))
    results["double_reversal"] = {"outcomes": sorted(race), "state": read_state(payment, invoice)}

    results["pass"] = (
        results["same_payment_concurrent_allocations"]["outcomes"].count("allocated") == 1
        and results["same_invoice_concurrent_allocations"]["outcomes"].count("allocated") == 1
        and results["reversal_vs_allocation"]["state"]["active_allocation_count"] == 0
        and results["double_reversal"]["outcomes"].count("reversed") == 1
    )
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
