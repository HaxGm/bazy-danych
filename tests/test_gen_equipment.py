"""Testy części Osoby 2: python -m unittest discover -s tests -v"""

import sys
import unittest
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# generatory leżą w scripts/, więc dodajemy ten folder do ścieżki importów
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import COLUMNS, SEED, TODAY, fake, rng, sql_insert
from gen_equipment import MODEL_CATALOG, generate_equipment


class EquipmentTests(unittest.TestCase):
    def setUp(self):
        fake.seed_instance(SEED)
        rng.seed(SEED)

    def test_default_dataset_matches_database_contract(self):
        rows = generate_equipment(150)
        self.assertEqual(len(rows), 150)
        self.assertEqual([row["equipment_id"] for row in rows], list(range(1, 151)))
        self.assertEqual(len({row["serial_number"] for row in rows}), 150)
        for row in rows:
            with self.subTest(equipment_id=row["equipment_id"]):
                self.assertEqual(set(row), set(COLUMNS["equipment"]))
                for field, limit in (
                    ("name", 100), ("category", 50),
                    ("manufacturer", 50), ("serial_number", 50),
                ):
                    self.assertIsInstance(row[field], str)
                    self.assertTrue(0 < len(row[field]) <= limit)
                self.assertTrue(row["description"])
                for field in ("daily_rate", "deposit"):
                    self.assertIsInstance(row[field], Decimal)
                    self.assertEqual(row[field].as_tuple().exponent, -2)
                    self.assertLess(row[field], Decimal("100000000"))
                self.assertGreater(row["daily_rate"], 0)
                self.assertGreaterEqual(row["deposit"], 0)
                self.assertIs(type(row["purchase_date"]), date)
                self.assertLess(row["purchase_date"], TODAY)
                self.assertGreaterEqual(
                    row["purchase_date"], TODAY - timedelta(days=3 * 365)
                )

    def test_default_dataset_covers_models_categories_and_statuses(self):
        rows = generate_equipment(150)
        self.assertEqual(
            Counter(row["category"] for row in rows),
            {"laptop": 30, "camera": 30, "projector": 30, "console": 30, "drone": 30},
        )
        model_counts = Counter((row["manufacturer"], row["name"]) for row in rows)
        self.assertEqual(len(model_counts), 15)
        self.assertEqual(set(model_counts.values()), {10})
        statuses = Counter(row["status"] for row in rows)
        self.assertEqual(set(statuses), {"available", "maintenance", "retired"})
        self.assertGreater(statuses["available"], 120)
        for status in ("maintenance", "retired"):
            self.assertTrue(1 <= statuses[status] <= 15)

    def test_empty_negative_and_nonstandard_sizes(self):
        self.assertEqual(generate_equipment(0), [])
        with self.assertRaises(ValueError):
            generate_equipment(-1)
        for size in (1, 14, 15, 16, 151, 1000):
            with self.subTest(size=size):
                rows = generate_equipment(size)
                self.assertEqual(len(rows), size)
                self.assertEqual(len({row["serial_number"] for row in rows}), size)
                self.assertEqual(rows[-1]["equipment_id"], size)

    def test_same_seed_reproduces_entire_dataset(self):
        first = generate_equipment(150)
        fake.seed_instance(SEED)
        rng.seed(SEED)
        self.assertEqual(first, generate_equipment(150))

    def test_rental_status_update_does_not_change_other_units_or_catalog(self):
        rows = generate_equipment(150)
        other_status = rows[15]["status"]  # ten sam model, inny egzemplarz
        rows[0]["status"] = "rented"
        rows[0]["daily_rate"] = Decimal("1.00")
        self.assertEqual(rows[15]["status"], other_status)
        self.assertNotEqual(rows[15]["daily_rate"], Decimal("1.00"))
        self.assertNotIn("status", MODEL_CATALOG[0])
        self.assertNotEqual(MODEL_CATALOG[0]["daily_rate"], Decimal("1.00"))

    def test_shared_sql_writer_accepts_equipment(self):
        sql = sql_insert("equipment", generate_equipment(150))
        self.assertTrue(sql.startswith("INSERT INTO equipment ("))
        self.assertEqual(sql.count("\n  ("), 150)
        self.assertNotIn("NULL", sql)
        self.assertTrue(sql.endswith(";\n"))


if __name__ == "__main__":
    unittest.main()
