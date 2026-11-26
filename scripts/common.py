"""Wspólne elementy generatora danych: ziarno, Faker, kolumny tabel i pomocnicze funkcje SQL.

Kontrakt dla wszystkich gen_*.py:
- każda funkcja zwraca listę słowników,
- klucze słownika to nazwy kolumn z COLUMNS (dodatkowe klucze są ignorowane przy zapisie),
- id nadajemy jawnie: 1, 2, 3, ... (np. "customer_id": 1),
- kwoty jako Decimal (funkcja money), daty jako date, znaczniki czasu jako datetime.
"""

import random
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from faker import Faker

SEED = 676767

# Stała "dzisiejsza" data, żeby dane nie zmieniały się w zależności od dnia uruchomienia.
TODAY = date(2026, 11, 26)

Faker.seed(SEED)
fake = Faker("pl_PL")
rng = random.Random(SEED)

# Kolumny zgodne z docs/schema.dbml.
COLUMNS = {
    "customers": [
        "customer_id", "first_name", "last_name", "address", "phone_number",
        "email", "nip", "registration_date",
    ],
    "equipment": [
        "equipment_id", "name", "category", "manufacturer", "serial_number",
        "description", "daily_rate", "deposit", "status", "purchase_date",
    ],
    "rentals": [
        "rental_id", "customer_id", "rental_date", "due_date", "return_date",
        "is_cancelled",
    ],
    "rental_items": [
        "rental_item_id", "rental_id", "equipment_id", "daily_rate", "deposit",
        "penalty", "return_notes", "is_cancelled",
    ],
    "payments": [
        "payment_id", "rental_id", "payment_date", "amount", "method", "type",
    ],
}

# Kolumna klucza głównego każdej tabeli (potrzebna do setval).
PRIMARY_KEYS = {table: cols[0] for table, cols in COLUMNS.items()}

# Wartości typów wyliczeniowych.
EQUIPMENT_STATUSES = ["available", "rented", "maintenance", "retired"]
PAYMENT_METHODS = ["cash", "card", "bank_transfer", "blik"]
PAYMENT_TYPES = ["rental_fee", "deposit", "deposit_refund", "penalty"]

# Kara za każdy dzień spóźnienia: daily_rate * PENALTY_MULTIPLIER (na pozycję).
PENALTY_MULTIPLIER = Decimal("1.5")


def money(value) -> Decimal:
    """Zaokrągla kwotę do 2 miejsc po przecinku."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def sql_literal(value) -> str:
    """Zamienia wartość Pythona na literał SQL."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        return str(money(value))
    if isinstance(value, datetime):  # przed date, bo datetime dziedziczy po date
        return "'" + value.replace(microsecond=0).isoformat(sep=" ") + "'"
    if isinstance(value, date):
        return "'" + value.isoformat() + "'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise TypeError(f"Nieobsługiwany typ wartości: {type(value).__name__} ({value!r})")


def sql_insert(table: str, rows: list[dict], batch_size: int = 500) -> str:
    """Zamienia listę słowników na INSERT INTO ... VALUES ... (po batch_size wierszy)."""
    if not rows:
        return f"-- {table}: brak danych\n"

    columns = COLUMNS[table]
    statements = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        values = ",\n".join(
            "  (" + ", ".join(sql_literal(row.get(col)) for col in columns) + ")"
            for row in batch
        )
        statements.append(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values};\n"
        )
    return "\n".join(statements)


def sql_setval(table: str) -> str:
    """Ustawia sekwencję klucza głównego na MAX(id), żeby kolejne INSERT-y bez id nie kolidowały."""
    pk = PRIMARY_KEYS[table]
    return (
        f"SELECT setval(pg_get_serial_sequence('{table}', '{pk}'), "
        f"COALESCE((SELECT MAX({pk}) FROM {table}), 1), "
        f"(SELECT COUNT(*) > 0 FROM {table}));\n"
    )
