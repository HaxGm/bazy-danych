"""Klienci (Osoba 1)."""

from common import TODAY, fake, rng


def generate_customers(n: int) -> list[dict]:
    """Zwraca n klientów; klucze jak w COLUMNS["customers"], customer_id = 1..n.

    TODO:
    - osoby prywatne i ok. 20% firm (nip z fake.company_vat(), u pozostałych None),
    - unikalne e-maile (fake.unique),
    - telefon bez spacji: 9 cyfr albo +48 i 9 cyfr,
    - registration_date z ostatnich 2-3 lat przed TODAY.
    """
    return []
