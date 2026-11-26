"""Generuje sql/02_data.sql z danymi do wszystkich tabel."""


import argparse
from pathlib import Path

from common import COLUMNS, SEED, TODAY, sql_insert, sql_setval
from gen_customers import generate_customers
from gen_equipment import generate_equipment
from gen_rentals import generate_rentals

N_CUSTOMERS = 200
N_EQUIPMENT = 150
N_RENTALS = 1000

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "sql" / "02_data.sql"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="plik wynikowy")
    args = parser.parse_args()

    customers = generate_customers(N_CUSTOMERS)                      # Osoba 1
    equipment = generate_equipment(N_EQUIPMENT)                      # Osoba 2
    rentals, items, payments = generate_rentals(customers, equipment, N_RENTALS)  # Osoba 3
    # generate_rentals ustawia status "rented" bezpośrednio w słownikach equipment,
    # dlatego zapis do pliku jest dopiero po wygenerowaniu wszystkiego.

    data = {
        "customers": customers,
        "equipment": equipment,
        "rentals": rentals,
        "rental_items": items,
        "payments": payments,
    }

    parts = [
        "-- Wygenerowane przez scripts/generate_data.py, nie edytować ręcznie.\n"
        f"-- Ziarno: {SEED}, data odniesienia: {TODAY}\n\n"
        "BEGIN;\n"
    ]
    for table in COLUMNS:  # kolejność zgodna z kluczami obcymi
        parts.append(f"\n-- ===== {table} =====\n")
        parts.append(sql_insert(table, data[table]))
    parts.append("\n-- ===== sekwencje =====\n")
    parts.extend(sql_setval(table) for table in COLUMNS)
    parts.append("\nCOMMIT;\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(parts), encoding="utf-8")

    for table, rows in data.items():
        print(f"{table:<13} {len(rows):>6} wierszy")
    print(f"Zapisano: {args.out}")


if __name__ == "__main__":
    main()
