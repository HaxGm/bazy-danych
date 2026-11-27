"""Testy części Osoby 3: python -m unittest discover -s tests -v"""

import sys
import unittest
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# generatory leżą w scripts/, więc dodajemy ten folder do ścieżki importów
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import (COLUMNS, PAYMENT_METHODS, PAYMENT_TYPES, PENALTY_MULTIPLIER, SEED,
                    TODAY, fake, money, rng, sql_insert)
from gen_customers import generate_customers
from gen_equipment import generate_equipment
from gen_rentals import HISTORY_DAYS, generate_rentals


def reseed():
    fake.unique.clear()
    fake.seed_instance(SEED)
    rng.seed(SEED)


def build_dataset():
    """Ten sam przebieg co w generate_data.py: 200 klientów, 150 sprzętów, 1000 wypożyczeń."""
    reseed()
    customers = generate_customers(200)
    equipment = generate_equipment(150)
    statuses_before = {e["equipment_id"]: e["status"] for e in equipment}
    rentals, items, payments = generate_rentals(customers, equipment, 1000)
    return customers, equipment, statuses_before, rentals, items, payments


class RentalsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.customers, cls.equipment, cls.statuses_before,
         cls.rentals, cls.items, cls.payments) = build_dataset()
        cls.customer_by_id = {c["customer_id"]: c for c in cls.customers}
        cls.equipment_by_id = {e["equipment_id"]: e for e in cls.equipment}
        cls.rental_by_id = {r["rental_id"]: r for r in cls.rentals}
        cls.items_by_rental = defaultdict(list)
        for it in cls.items:
            cls.items_by_rental[it["rental_id"]].append(it)
        cls.payments_by_rental = defaultdict(list)
        for p in cls.payments:
            cls.payments_by_rental[p["rental_id"]].append(p)

    # ----- kontrakt -----

    def test_rows_match_database_contract(self):
        for table, rows in (("rentals", self.rentals), ("rental_items", self.items),
                            ("payments", self.payments)):
            with self.subTest(table=table):
                pk = COLUMNS[table][0]
                self.assertEqual([row[pk] for row in rows], list(range(1, len(rows) + 1)))
                for row in rows:
                    self.assertEqual(set(row), set(COLUMNS[table]))

        self.assertEqual(len(self.rentals), 1000)
        for r in self.rentals:
            self.assertIs(type(r["rental_date"]), datetime)
            self.assertIs(type(r["due_date"]), date)
            self.assertIsInstance(r["is_cancelled"], bool)
            self.assertIn(r["customer_id"], self.customer_by_id)
        for it in self.items:
            self.assertIn(it["rental_id"], self.rental_by_id)
            self.assertIn(it["equipment_id"], self.equipment_by_id)
            for field in ("daily_rate", "deposit", "penalty"):
                if it[field] is not None:
                    self.assertIsInstance(it[field], Decimal)
                    self.assertEqual(it[field].as_tuple().exponent, -2)
            if it["return_notes"] is not None:
                self.assertTrue(0 < len(it["return_notes"]) <= 500)

    def test_each_rental_has_1_to_4_distinct_items(self):
        for r in self.rentals:
            eq_ids = [it["equipment_id"] for it in self.items_by_rental[r["rental_id"]]]
            self.assertTrue(1 <= len(eq_ids) <= 4)
            self.assertEqual(len(eq_ids), len(set(eq_ids)))  # UNIQUE (rental_id, equipment_id)

    # ----- daty -----

    def test_dates_are_consistent(self):
        first_day = TODAY - timedelta(days=HISTORY_DAYS)
        for r in self.rentals:
            with self.subTest(rental_id=r["rental_id"]):
                self.assertTrue(first_day <= r["rental_date"].date() < TODAY)
                self.assertGreater(r["due_date"], r["rental_date"].date())
                if r["return_date"] is not None:
                    self.assertGreaterEqual(r["return_date"], r["rental_date"])
                    self.assertLess(r["return_date"].date(), TODAY)
                customer = self.customer_by_id[r["customer_id"]]
                self.assertLessEqual(customer["registration_date"], r["rental_date"].date())
        for it in self.items:
            r = self.rental_by_id[it["rental_id"]]
            eq = self.equipment_by_id[it["equipment_id"]]
            self.assertLess(eq["purchase_date"], r["rental_date"].date())

    def test_same_unit_is_never_rented_twice_at_once(self):
        spans = defaultdict(list)
        for it in self.items:
            r = self.rental_by_id[it["rental_id"]]
            if not it["is_cancelled"] and not r["is_cancelled"]:
                spans[it["equipment_id"]].append(
                    (r["rental_date"], r["return_date"] or datetime.max, r["rental_id"]))
        for eq_id, periods in spans.items():
            periods.sort()
            for (_, end1, r1), (start2, _, r2) in zip(periods, periods[1:]):
                with self.subTest(equipment_id=eq_id, rentals=(r1, r2)):
                    self.assertGreaterEqual(start2, end1)

    # ----- przypadki -----

    def test_all_scenarios_are_present(self):
        returned = [r for r in self.rentals if r["return_date"] is not None]
        open_ = [r for r in self.rentals if r["return_date"] is None and not r["is_cancelled"]]
        late = [r for r in returned if r["return_date"].date() > r["due_date"]]
        single_cancelled = [it for it in self.items if it["is_cancelled"]
                            and not self.rental_by_id[it["rental_id"]]["is_cancelled"]]
        self.assertGreater(len(returned) - len(late), 500)                     # w terminie
        self.assertGreater(len(late), 50)                                      # po terminie
        self.assertGreater(len(open_), 0)                                      # w toku
        self.assertTrue(any(r["due_date"] < TODAY for r in open_))             # przetrzymane
        self.assertTrue(any(r["due_date"] >= TODAY for r in open_))            # w toku, w terminie
        self.assertGreater(sum(r["is_cancelled"] for r in self.rentals), 10)   # anulowane
        self.assertGreater(len(single_cancelled), 0)                           # anulowane pozycje

    def test_cancelled_rentals(self):
        for r in self.rentals:
            if r["is_cancelled"]:
                with self.subTest(rental_id=r["rental_id"]):
                    self.assertIsNone(r["return_date"])
                    self.assertTrue(all(it["is_cancelled"] for it in self.items_by_rental[r["rental_id"]]))
                    self.assertEqual(self.payments_by_rental[r["rental_id"]], [])
            else:
                # nieanulowane wypożyczenie ma co najmniej jedną aktywną pozycję
                self.assertTrue(any(not it["is_cancelled"] for it in self.items_by_rental[r["rental_id"]]))

    # ----- stawki i kary -----

    def test_rates_are_copied_from_equipment(self):
        for it in self.items:
            eq = self.equipment_by_id[it["equipment_id"]]
            self.assertEqual(it["daily_rate"], eq["daily_rate"])
            self.assertEqual(it["deposit"], eq["deposit"])

    def test_penalty_formula(self):
        for it in self.items:
            r = self.rental_by_id[it["rental_id"]]
            with self.subTest(rental_item_id=it["rental_item_id"]):
                if it["is_cancelled"] or r["return_date"] is None:
                    self.assertIsNone(it["penalty"])
                    self.assertIsNone(it["return_notes"])
                else:
                    days_late = max(0, (r["return_date"].date() - r["due_date"]).days)
                    self.assertEqual(it["penalty"],
                                     money(days_late * it["daily_rate"] * PENALTY_MULTIPLIER))

    # ----- płatności -----

    def test_payments_are_consistent_with_rentals(self):
        self.assertTrue(all(p["amount"] > 0 for p in self.payments))
        self.assertEqual({p["method"] for p in self.payments}, set(PAYMENT_METHODS))
        self.assertEqual({p["type"] for p in self.payments}, set(PAYMENT_TYPES))

        for r in self.rentals:
            if r["is_cancelled"]:
                continue
            with self.subTest(rental_id=r["rental_id"]):
                active = [it for it in self.items_by_rental[r["rental_id"]] if not it["is_cancelled"]]
                by_type = {p["type"]: p for p in self.payments_by_rental[r["rental_id"]]}
                self.assertEqual(len(by_type), len(self.payments_by_rental[r["rental_id"]]))

                days = (r["due_date"] - r["rental_date"].date()).days
                self.assertEqual(by_type["rental_fee"]["amount"],
                                 money(sum(it["daily_rate"] for it in active) * days))
                self.assertEqual(by_type["rental_fee"]["payment_date"], r["rental_date"])

                deposit = sum(it["deposit"] for it in active)
                penalty = sum(it["penalty"] or 0 for it in active)
                expected = {"rental_fee"}
                if deposit > 0:
                    expected.add("deposit")
                    self.assertEqual(by_type["deposit"]["amount"], deposit)
                if r["return_date"] is not None:
                    if deposit > 0:
                        expected.add("deposit_refund")
                        self.assertEqual(by_type["deposit_refund"]["amount"], deposit)
                        self.assertEqual(by_type["deposit_refund"]["payment_date"], r["return_date"])
                    if penalty > 0:
                        expected.add("penalty")
                        self.assertEqual(by_type["penalty"]["amount"], penalty)
                        self.assertEqual(by_type["penalty"]["payment_date"], r["return_date"])
                self.assertEqual(set(by_type), expected)

    # ----- statusy sprzętu -----

    def test_rented_status_matches_open_rentals(self):
        open_units = {
            it["equipment_id"] for it in self.items
            if not it["is_cancelled"]
            and not self.rental_by_id[it["rental_id"]]["is_cancelled"]
            and self.rental_by_id[it["rental_id"]]["return_date"] is None
        }
        rented = {e["equipment_id"] for e in self.equipment if e["status"] == "rented"}
        self.assertEqual(open_units, rented)
        self.assertGreater(len(rented), 0)
        # 'rented' dostaje tylko sprzęt, który był 'available'; reszta statusów bez zmian
        for e in self.equipment:
            before = self.statuses_before[e["equipment_id"]]
            if e["status"] == "rented":
                self.assertEqual(before, "available")
            else:
                self.assertEqual(e["status"], before)

    def test_retired_equipment_without_date_is_never_rented(self):
        retired = {eid for eid, s in self.statuses_before.items() if s == "retired"}
        self.assertTrue(retired)
        self.assertFalse(any(it["equipment_id"] in retired for it in self.items))

    def test_retired_equipment_with_date_is_returned_before_retirement(self):
        reseed()
        equipment = [{"equipment_id": i, "daily_rate": money(50), "deposit": money(300),
                      "status": "available", "purchase_date": date(2023, 1, 1)}
                     for i in range(1, 6)]
        equipment[0]["status"] = "retired"
        equipment[0]["_retired_date"] = date(2025, 6, 1)
        rentals, items, _ = generate_rentals([{"customer_id": 1}], equipment, 300)
        by_id = {r["rental_id"]: r for r in rentals}
        used = [it for it in items if it["equipment_id"] == 1 and not it["is_cancelled"]]
        self.assertTrue(used)
        for it in used:
            r = by_id[it["rental_id"]]
            self.assertIsNotNone(r["return_date"])
            self.assertLess(r["return_date"].date(), date(2025, 6, 1))
        self.assertEqual(equipment[0]["status"], "retired")

    # ----- pozostałe -----

    def test_empty_inputs_give_empty_results(self):
        self.assertEqual(generate_rentals([], [], 1000), ([], [], []))
        self.assertEqual(generate_rentals(self.customers, [], 1000), ([], [], []))

    def test_same_seed_reproduces_entire_dataset(self):
        _, _, _, rentals, items, payments = build_dataset()
        self.assertEqual(rentals, self.rentals)
        self.assertEqual(items, self.items)
        self.assertEqual(payments, self.payments)

    def test_shared_sql_writer_accepts_rentals(self):
        for table, rows in (("rentals", self.rentals), ("rental_items", self.items),
                            ("payments", self.payments)):
            with self.subTest(table=table):
                sql = sql_insert(table, rows)
                self.assertTrue(sql.startswith(f"INSERT INTO {table} ("))
                self.assertEqual(sql.count("\n  ("), len(rows))
                self.assertTrue(sql.endswith(";\n"))


if __name__ == "__main__":
    unittest.main()
