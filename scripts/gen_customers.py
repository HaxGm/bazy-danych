"""Klienci (Osoba 1)."""

import re
from datetime import timedelta

from common import TODAY, fake, rng

BUSINESS_SHARE = 0.2          # część klientów biznesowych (z NIP)
REGISTRATION_YEARS = 3        # rejestracje z ostatnich lat przed TODAY
INTERNATIONAL_PREFIX_SHARE = 0.3  # część telefonów zapisanych z +48

_POLISH_TO_ASCII = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def _ascii_slug(text: str) -> str:
    """'Zięcik-Nowak' -> 'ziecik-nowak' (do adresów e-mail)."""
    text = text.translate(_POLISH_TO_ASCII).lower()
    return re.sub(r"[^a-z0-9-]", "", text)


def _phone_number() -> str:
    """9 cyfr (np. 327406812) albo +48 i 9 cyfr; bez spacji i nawiasów."""
    digits = re.sub(r"\D", "", fake.phone_number())[-9:]
    if rng.random() < INTERNATIONAL_PREFIX_SHARE:
        return "+48" + digits
    return digits


def _email(first_name: str, last_name: str, is_business: bool, used: set[str]) -> str:
    """Unikalny e-mail z imienia i nazwiska; firmy w domenie firmowej."""
    first, last = _ascii_slug(first_name), _ascii_slug(last_name)
    local = rng.choice([f"{first}.{last}", f"{first[0]}{last}", f"{first}{last}", f"{last}.{first}"])
    domain = fake.domain_name() if is_business else fake.free_email_domain()

    email = f"{local}@{domain}"
    while email in used:
        email = f"{local}{rng.randint(1, 999)}@{domain}"
    used.add(email)
    return email


def generate_customers(n: int) -> list[dict]:
    """Zwraca n klientów; klucze jak w COLUMNS["customers"], customer_id = 1..n.

    Id rosną razem z registration_date (klient 1 zarejestrował się najwcześniej).
    """
    first_day = TODAY - timedelta(days=365 * REGISTRATION_YEARS)
    span_days = (TODAY - first_day).days

    used_emails: set[str] = set()
    customers = []
    for _ in range(n):
        if rng.random() < 0.5:
            first_name, last_name = fake.first_name_female(), fake.last_name_female()
        else:
            first_name, last_name = fake.first_name_male(), fake.last_name_male()

        is_business = rng.random() < BUSINESS_SHARE
        customers.append({
            "first_name": first_name,
            "last_name": last_name,
            "address": fake.address().replace("\n", ", "),
            "phone_number": _phone_number(),
            "email": _email(first_name, last_name, is_business, used_emails),
            "nip": fake.unique.company_vat() if is_business else None,
            "registration_date": first_day + timedelta(days=rng.randint(0, span_days)),
        })

    customers.sort(key=lambda c: c["registration_date"])
    for customer_id, customer in enumerate(customers, start=1):
        customer["customer_id"] = customer_id
    return customers
