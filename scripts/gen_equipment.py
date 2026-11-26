"""Sprzęt (Osoba 2)."""

from common import TODAY, fake, money, rng


def generate_equipment(n: int) -> list[dict]:
    """Zwraca n egzemplarzy; klucze jak w COLUMNS["equipment"], equipment_id = 1..n.

    TODO:
    - katalog modeli: laptop, camera, projector, console, drone + producenci,
    - po kilka egzemplarzy modelu, unikalne serial_number,
    - daily_rate > 0 i deposit >= 0 zależne od kategorii (money(...)),
    - status: głównie "available", kilka "maintenance" i "retired"
      ("rented" ustawia generate_rentals),
    - purchase_date przed TODAY.
    """
    return []
